"""
Minimal Levenberg-Marquardt solver vendored from EPro-PnP and cleaned for
general batch shapes.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .common import evaluate_pnp, pnp_denormalize, pnp_normalize


def solve_wrapper(b, A):
    if A.numel() == 0:
        return b + A.reshape_as(b)
    try:
        return torch.linalg.solve(A, b)
    except torch.linalg.LinAlgError:
        return torch.linalg.pinv(A) @ b


class LMSolver(nn.Module):
    def __init__(self, dof=4, num_iter=10, min_lm_diagonal=1e-6,
                 max_lm_diagonal=1e32, min_relative_decrease=1e-3,
                 initial_trust_region_radius=30.0, max_trust_region_radius=1e16,
                 eps=1e-5, normalize=False, init_solver=None):
        super(LMSolver, self).__init__()
        self.dof = dof
        self.num_iter = num_iter
        self.min_lm_diagonal = min_lm_diagonal
        self.max_lm_diagonal = max_lm_diagonal
        self.min_relative_decrease = min_relative_decrease
        self.initial_trust_region_radius = initial_trust_region_radius
        self.max_trust_region_radius = max_trust_region_radius
        self.eps = eps
        self.normalize = normalize
        self.init_solver = init_solver

    def forward(self, x3d, x2d, w2d, camera, cost_fun, with_pose_opt_plus=False,
                pose_init=None, normalize_override=None, **kwargs):
        normalize = normalize_override if isinstance(normalize_override, bool) else self.normalize
        if normalize:
            transform, x3d, pose_init = pnp_normalize(x3d, pose_init, detach_transformation=True)
        pose_opt, pose_cov, cost = self.solve(x3d, x2d, w2d, camera, cost_fun, pose_init=pose_init, **kwargs)
        if with_pose_opt_plus:
            step = self.gn_step(x3d, x2d, w2d, pose_opt, camera, cost_fun)
            pose_opt_plus = self.pose_add(pose_opt, step, camera)
        else:
            pose_opt_plus = None
        if normalize:
            pose_opt = pnp_denormalize(transform, pose_opt)
            if pose_cov is not None:
                raise NotImplementedError('Normalized covariance unsupported')
            if pose_opt_plus is not None:
                pose_opt_plus = pnp_denormalize(transform, pose_opt_plus)
        return pose_opt, pose_cov, cost, pose_opt_plus

    def solve(self, x3d, x2d, w2d, camera, cost_fun, pose_init=None, cost_init=None,
              with_pose_cov=False, with_cost=False, force_init_solve=False, fast_mode=False):
        with torch.no_grad():
            num_obj, num_pts, _ = x2d.size()
            tensor_kwargs = dict(dtype=x2d.dtype, device=x2d.device)
            if num_obj == 0:
                pose_opt = torch.empty((0, 4 if self.dof == 4 else 7), **tensor_kwargs)
                pose_cov = torch.empty((0, self.dof, self.dof), **tensor_kwargs) if with_pose_cov else None
                cost = torch.empty((0,), **tensor_kwargs) if with_cost else None
                return pose_opt, pose_cov, cost

            evaluate_fun = lambda pose, **kw: evaluate_pnp(
                x3d=x3d, x2d=x2d, w2d=w2d, camera=camera, cost_fun=cost_fun,
                clip_jac=not fast_mode, pose=pose, **kw)

            if pose_init is None or force_init_solve:
                assert self.init_solver is not None
                if pose_init is None:
                    pose_opt, _, _ = self.init_solver.solve(x3d, x2d, w2d, camera, cost_fun, fast_mode=fast_mode)
                else:
                    if cost_init is None:
                        cost_init = evaluate_fun(pose=pose_init, out_cost=True)[1]
                    pose_init_solve, _, cost_init_solve = self.init_solver.solve(
                        x3d, x2d, w2d, camera, cost_fun, with_cost=True, fast_mode=fast_mode)
                    use_init = cost_init < cost_init_solve
                    pose_init_solve[use_init] = pose_init[use_init]
                    pose_opt = pose_init_solve
            else:
                pose_opt = pose_init.clone()

            jac = torch.empty((num_obj, num_pts * 2, self.dof), **tensor_kwargs)
            residual = torch.empty((num_obj, num_pts * 2), **tensor_kwargs)
            cost = torch.empty((num_obj,), **tensor_kwargs)

            if fast_mode:
                for _ in range(self.num_iter):
                    evaluate_fun(pose=pose_opt, out_jacobian=jac, out_residual=residual, out_cost=cost)
                    jac_t = jac.transpose(-1, -2)
                    jtj = jac_t @ jac
                    diagonal = torch.diagonal(jtj, dim1=-2, dim2=-1)
                    diagonal += self.eps
                    gradient = jac_t @ residual.unsqueeze(-1)
                    if self.dof == 4:
                        pose_opt -= solve_wrapper(gradient, jtj).squeeze(-1)
                    else:
                        step = -solve_wrapper(gradient, jtj).squeeze(-1)
                        pose_opt[..., :3] += step[..., :3]
                        pose_opt[..., 3:] = F.normalize(
                            pose_opt[..., 3:] + (
                                camera.get_quaternion_transfrom_mat(pose_opt[..., 3:]) @ step[..., 3:, None]
                            ).squeeze(-1), dim=-1)
            else:
                evaluate_fun(pose=pose_opt, out_jacobian=jac, out_residual=residual, out_cost=cost)
                jac_new = torch.empty_like(jac)
                residual_new = torch.empty_like(residual)
                cost_new = torch.empty_like(cost)
                radius = x2d.new_full((num_obj,), self.initial_trust_region_radius)
                decrease_factor = x2d.new_full((num_obj,), 2.0)
                step_is_successful = x2d.new_zeros((num_obj,), dtype=torch.bool)
                for _ in range(self.num_iter):
                    self._lm_iter(
                        pose_opt, jac, residual, cost,
                        jac_new, residual_new, cost_new,
                        step_is_successful, radius, decrease_factor,
                        evaluate_fun, camera)
                if with_pose_cov:
                    jac[step_is_successful] = jac_new[step_is_successful]
                    jtj = jac.transpose(-1, -2) @ jac
                    diagonal = torch.diagonal(jtj, dim1=-2, dim2=-1)
                    diagonal += self.eps
                if with_cost:
                    cost[step_is_successful] = cost_new[step_is_successful]

            pose_cov = torch.inverse(jtj) if with_pose_cov else None
            if not with_cost:
                cost = None
            return pose_opt, pose_cov, cost

    def _lm_iter(self, pose_opt, jac, residual, cost, jac_new, residual_new, cost_new,
                 step_is_successful, radius, decrease_factor, evaluate_fun, camera):
        jac[step_is_successful] = jac_new[step_is_successful]
        residual[step_is_successful] = residual_new[step_is_successful]
        cost[step_is_successful] = cost_new[step_is_successful]

        residual_ = residual.unsqueeze(-1)
        jac_t = jac.transpose(-1, -2)
        jtj = jac_t @ jac
        jtj_lm = jtj.clone()
        diagonal = torch.diagonal(jtj_lm, dim1=-2, dim2=-1)
        diagonal += (
            diagonal.clamp(min=self.min_lm_diagonal, max=self.max_lm_diagonal) / radius[:, None] + self.eps
        ).clamp(min=self.eps)
        gradient = jac_t @ residual_
        step_ = -solve_wrapper(gradient, jtj_lm)

        pose_new = self.pose_add(pose_opt, step_.squeeze(-1), camera)
        evaluate_fun(pose=pose_new, out_jacobian=jac_new, out_residual=residual_new, out_cost=cost_new)

        model_cost_change = -(step_.transpose(-1, -2) @ ((jtj @ step_) / 2 + gradient)).flatten()
        relative_decrease = (cost - cost_new) / model_cost_change.clamp(min=self.eps)
        torch.bitwise_and(
            relative_decrease >= self.min_relative_decrease,
            model_cost_change > 0.0,
            out=step_is_successful,
        )

        pose_opt[step_is_successful] = pose_new[step_is_successful]
        radius[step_is_successful] /= (
            1.0 - (2.0 * relative_decrease[step_is_successful] - 1.0) ** 3
        ).clamp(min=1.0 / 3.0)
        radius.clamp_(max=self.max_trust_region_radius, min=self.eps)
        decrease_factor.masked_fill_(step_is_successful, 2.0)

        radius[~step_is_successful] /= decrease_factor[~step_is_successful]
        decrease_factor[~step_is_successful] = decrease_factor[~step_is_successful] * 2.0

    def gn_step(self, x3d, x2d, w2d, pose, camera, cost_fun):
        residual, _, jac = evaluate_pnp(
            x3d, x2d, w2d, pose, camera, cost_fun,
            out_jacobian=True, out_residual=True)
        jac_t = jac.transpose(-1, -2)
        jtj = jac_t @ jac
        jtj = jtj + torch.eye(self.dof, device=jtj.device, dtype=jtj.dtype) * self.eps
        gradient = jac_t @ residual.unsqueeze(-1)
        step = -solve_wrapper(gradient, jtj).squeeze(-1)
        return step

    def pose_add(self, pose_opt, step, camera):
        if self.dof == 4:
            return pose_opt + step
        return torch.cat(
            (
                pose_opt[..., :3] + step[..., :3],
                F.normalize(
                    pose_opt[..., 3:] + (
                        camera.get_quaternion_transfrom_mat(pose_opt[..., 3:]) @ step[..., 3:, None]
                    ).squeeze(-1),
                    dim=-1,
                ),
            ),
            dim=-1,
        )


class RSLMSolver(LMSolver):
    def __init__(self, num_points=16, num_proposals=64, num_iter=3, **kwargs):
        super(RSLMSolver, self).__init__(num_iter=num_iter, **kwargs)
        self.num_points = num_points
        self.num_proposals = num_proposals

    def center_based_init(self, x2d, x3d, camera, eps=1e-6):
        x2dc = solve_wrapper(
            F.pad(x2d, [0, 1], mode='constant', value=1.).transpose(-1, -2),
            camera.cam_mats,
        ).transpose(-1, -2)
        x2dc = x2dc[..., :2] / x2dc[..., 2:].clamp(min=eps)
        x2dc_std, x2dc_mean = torch.std_mean(x2dc, dim=-2)
        x3d_std = torch.std(x3d, dim=-2)
        if self.dof == 4:
            return F.pad(
                x2dc_mean, [0, 1], mode='constant', value=1.
            ) * (x3d_std[..., 1] / x2dc_std[..., 1].clamp(min=eps)).unsqueeze(-1)
        return F.pad(
            x2dc_mean, [0, 1], mode='constant', value=1.
        ) * (
            math.sqrt(2 / 3) * x3d_std.norm(dim=-1) / x2dc_std.norm(dim=-1).clamp(min=eps)
        ).unsqueeze(-1)

    def solve(self, x3d, x2d, w2d, camera, cost_fun, **kwargs):
        with torch.no_grad():
            bs, pn, _ = x2d.size()
            if bs == 0:
                pose = x2d.new_empty((0, 4 if self.dof == 4 else 7))
                min_cost = x2d.new_empty((0,))
                return pose, None, min_cost

            mean_weight = w2d.mean(dim=-1).reshape(1, bs, pn).expand(self.num_proposals, -1, -1)
            inds = torch.multinomial(
                mean_weight.reshape(-1, pn), self.num_points
            ).reshape(self.num_proposals, bs, self.num_points)
            bs_inds = torch.arange(bs, device=inds.device)
            inds = inds + (bs_inds * pn)[None, :, None]

            x2d_samples = x2d.reshape(-1, 2)[inds]
            x3d_samples = x3d.reshape(-1, 3)[inds]
            w2d_samples = w2d.reshape(-1, 2)[inds]

            pose_init = x2d.new_empty((self.num_proposals, bs, 4 if self.dof == 4 else 7))
            pose_init[..., :3] = self.center_based_init(x2d, x3d, camera)
            if self.dof == 4:
                pose_init[..., 3] = torch.rand(
                    (self.num_proposals, bs), dtype=x2d.dtype, device=x2d.device
                ) * (2 * math.pi)
            else:
                pose_init[..., 3:] = torch.randn(
                    (self.num_proposals, bs, 4), dtype=x2d.dtype, device=x2d.device
                )
                q_norm = pose_init[..., 3:].norm(dim=-1)
                pose_init[..., 3:] /= q_norm.unsqueeze(-1).clamp(min=self.eps)
                pose_init.view(-1, 7)[(q_norm < self.eps).flatten(), 3:] = x2d.new_tensor([1, 0, 0, 0])

            camera_expand = camera.shallow_copy()
            camera_expand.repeat_(self.num_proposals)
            cost_fun_expand = cost_fun.shallow_copy()
            cost_fun_expand.repeat_(self.num_proposals)

            pose, _, _ = super(RSLMSolver, self).solve(
                x3d_samples.reshape(self.num_proposals * bs, self.num_points, 3),
                x2d_samples.reshape(self.num_proposals * bs, self.num_points, 2),
                w2d_samples.reshape(self.num_proposals * bs, self.num_points, 2),
                camera_expand,
                cost_fun_expand,
                pose_init=pose_init.reshape(self.num_proposals * bs, pose_init.size(-1)),
                **kwargs
            )
            pose = pose.reshape(self.num_proposals, bs, pose.size(-1))
            cost = evaluate_pnp(x3d, x2d, w2d, pose, camera, cost_fun, out_cost=True)[1]
            min_cost, min_cost_ind = cost.min(dim=0)
            pose = pose[min_cost_ind, torch.arange(bs, device=pose.device)]
            return pose, None, min_cost
