"""
Minimal probabilistic PnP modules vendored from EPro-PnP for 6DoF training.
"""

import math

import torch

from .common import evaluate_pnp, pnp_denormalize, pnp_normalize
from .distributions import AngularCentralGaussian, MultivariateStudentT


def cholesky_wrapper(mat, default_diag=None, force_cpu=False):
    device = mat.device
    chol_input = mat.cpu() if force_cpu else mat
    try:
        tril = torch.linalg.cholesky(chol_input, upper=False)
    except RuntimeError:
        n_dims = chol_input.size(-1)
        tril = []
        default_tril_single = torch.diag(chol_input.new_tensor(default_diag)) if default_diag is not None \
            else torch.eye(n_dims, dtype=chol_input.dtype, device=chol_input.device)
        for cov in chol_input.reshape(-1, n_dims, n_dims):
            try:
                tril.append(torch.linalg.cholesky(cov, upper=False))
            except RuntimeError:
                tril.append(default_tril_single)
        tril = torch.stack(tril, dim=0).reshape(chol_input.shape)
    return tril.to(device)


class EProPnPBase(torch.nn.Module):
    def __init__(self, mc_samples=512, num_iter=4, normalize=False, eps=1e-5, solver=None):
        super(EProPnPBase, self).__init__()
        assert num_iter > 0
        assert mc_samples % num_iter == 0
        self.mc_samples = mc_samples
        self.num_iter = num_iter
        self.iter_samples = self.mc_samples // self.num_iter
        self.eps = eps
        self.normalize = normalize
        self.solver = solver

    def forward(self, *args, **kwargs):
        return self.solver(*args, **kwargs)

    def monte_carlo_forward(self, x3d, x2d, w2d, camera, cost_fun,
                            pose_init=None, force_init_solve=True, **kwargs):
        if self.normalize:
            transform, x3d, pose_init = pnp_normalize(x3d, pose_init, detach_transformation=True)

        assert x3d.dim() == x2d.dim() == w2d.dim() == 3
        num_obj = x3d.size(0)

        evaluate_fun = lambda pose: evaluate_pnp(
            x3d=x3d, x2d=x2d, w2d=w2d, camera=camera, cost_fun=cost_fun,
            pose=pose, out_cost=True)
        cost_init = evaluate_fun(pose=pose_init)[1] if pose_init is not None else None

        pose_opt, pose_cov, cost, pose_opt_plus = self.solver(
            x3d, x2d, w2d, camera, cost_fun,
            pose_init=pose_init, cost_init=cost_init,
            with_pose_cov=True, force_init_solve=force_init_solve,
            normalize_override=False, **kwargs)

        if num_obj > 0:
            pose_samples = x3d.new_empty((self.num_iter, self.iter_samples) + pose_opt.size())
            logprobs = x3d.new_empty((self.num_iter, self.num_iter, self.iter_samples, num_obj))
            cost_pred = x3d.new_empty((self.num_iter, self.iter_samples, num_obj))
            distr_params = self.allocate_buffer(num_obj, dtype=x3d.dtype, device=x3d.device)

            with torch.no_grad():
                self.initial_fit(pose_opt, pose_cov, camera, *distr_params)

            for i in range(self.num_iter):
                new_trans_distr, new_rot_distr = self.gen_new_distr(i, *distr_params)
                pose_samples[i, :, :, :3] = new_trans_distr.sample((self.iter_samples,))
                pose_samples[i, :, :, 3:] = new_rot_distr.sample((self.iter_samples,))
                cost_pred[i] = evaluate_fun(pose=pose_samples[i])[1]

                logprobs[i, :i + 1] = new_trans_distr.log_prob(pose_samples[:i + 1, :, :, :3]) \
                    + new_rot_distr.log_prob(pose_samples[:i + 1, :, :, 3:])
                if i > 0:
                    old_trans_distr, old_rot_distr = self.gen_old_distr(i, *distr_params)
                    logprobs[:i, i] = old_trans_distr.log_prob(pose_samples[i, :, :, :3]) \
                        + old_rot_distr.log_prob(pose_samples[i, :, :, 3:])

                mix_logprobs = torch.logsumexp(logprobs[:i + 1, :i + 1], dim=0) - math.log(i + 1)
                pose_sample_logweights = -cost_pred[:i + 1] - mix_logprobs

                if i == self.num_iter - 1:
                    break
                with torch.no_grad():
                    self.estimate_params(
                        i,
                        pose_samples[:i + 1].reshape(((i + 1) * self.iter_samples,) + pose_opt.size()),
                        pose_sample_logweights.reshape((i + 1) * self.iter_samples, num_obj),
                        *distr_params)

            pose_samples = pose_samples.reshape((self.mc_samples,) + pose_opt.size())
            pose_sample_logweights = pose_sample_logweights.reshape(self.mc_samples, num_obj)
        else:
            pose_samples = x2d.new_zeros((self.mc_samples,) + pose_opt.size())
            pose_sample_logweights = x2d.new_zeros((self.mc_samples, 0))

        if self.normalize:
            pose_opt = pnp_denormalize(transform, pose_opt)
            pose_samples = pnp_denormalize(transform, pose_samples)
            if pose_opt_plus is not None:
                pose_opt_plus = pnp_denormalize(transform, pose_opt_plus)

        return pose_opt, cost, pose_opt_plus, pose_samples, pose_sample_logweights, cost_init


class EProPnP6DoF(EProPnPBase):
    def __init__(self, *args, acg_mle_iter=3, acg_dispersion=0.001, **kwargs):
        super(EProPnP6DoF, self).__init__(*args, **kwargs)
        self.acg_mle_iter = acg_mle_iter
        self.acg_dispersion = acg_dispersion

    def allocate_buffer(self, num_obj, dtype=torch.float32, device=None):
        trans_mode = torch.empty((self.num_iter, num_obj, 3), dtype=dtype, device=device)
        trans_cov_tril = torch.empty((self.num_iter, num_obj, 3, 3), dtype=dtype, device=device)
        rot_cov_tril = torch.empty((self.num_iter, num_obj, 4, 4), dtype=dtype, device=device)
        return trans_mode, trans_cov_tril, rot_cov_tril

    def initial_fit(self, pose_opt, pose_cov, camera, trans_mode, trans_cov_tril, rot_cov_tril):
        trans_mode[0], rot_mode = pose_opt.split([3, 4], dim=-1)
        trans_cov_tril[0] = cholesky_wrapper(pose_cov[:, :3, :3])
        eye_4 = torch.eye(4, dtype=pose_opt.dtype, device=pose_opt.device)
        transform_mat = camera.get_quaternion_transfrom_mat(rot_mode)
        pseudo_inverse_cov = torch.pinverse(pose_cov[:, 3:, 3:])
        rot_cov = (transform_mat @ pseudo_inverse_cov @ transform_mat.transpose(-1, -2) + eye_4).inverse()
        rot_cov.div_(rot_cov.diagonal(offset=0, dim1=-2, dim2=-1).sum(-1)[..., None, None])
        rot_cov_tril[0] = cholesky_wrapper(
            rot_cov + rot_cov.det()[:, None, None] ** 0.25 * (self.acg_dispersion * eye_4)
        )

    @staticmethod
    def gen_new_distr(iter_id, trans_mode, trans_cov_tril, rot_cov_tril):
        new_trans_distr = MultivariateStudentT(3, trans_mode[iter_id], trans_cov_tril[iter_id])
        new_rot_distr = AngularCentralGaussian(rot_cov_tril[iter_id], validate_args=False)
        return new_trans_distr, new_rot_distr

    @staticmethod
    def gen_old_distr(iter_id, trans_mode, trans_cov_tril, rot_cov_tril):
        mix_trans_distr = MultivariateStudentT(3, trans_mode[:iter_id, None], trans_cov_tril[:iter_id, None])
        mix_rot_distr = AngularCentralGaussian(rot_cov_tril[:iter_id, None], validate_args=False)
        return mix_trans_distr, mix_rot_distr

    def estimate_params(self, iter_id, pose_samples, pose_sample_logweights,
                        trans_mode, trans_cov_tril, rot_cov_tril):
        sample_weights_norm = torch.softmax(pose_sample_logweights, dim=0)
        trans_mode[iter_id + 1] = (sample_weights_norm[..., None] * pose_samples[..., :3]).sum(dim=0)
        trans_dev = pose_samples[..., :3] - trans_mode[iter_id + 1]
        trans_cov = (sample_weights_norm[..., None, None] * trans_dev.unsqueeze(-1) * trans_dev.unsqueeze(-2)).sum(dim=0)
        trans_cov_tril[iter_id + 1] = cholesky_wrapper(trans_cov)

        eye_4 = torch.eye(4, dtype=pose_samples.dtype, device=pose_samples.device)
        rot = pose_samples[..., 3:]
        r_r_t = rot[:, :, :, None] * rot[:, :, None, :]
        rot_cov = eye_4.expand(pose_samples.size(1), 4, 4).clone()
        for _ in range(self.acg_mle_iter):
            M = rot[:, :, None, :] @ rot_cov.inverse() @ rot[:, :, :, None]
            invM_weighted = sample_weights_norm[..., None, None] / M.clamp(min=self.eps)
            invM_weighted_norm = invM_weighted / invM_weighted.sum(dim=0).clamp(min=self.eps)
            rot_cov = (invM_weighted_norm * r_r_t).sum(dim=0) + eye_4 * self.eps
        rot_cov_tril[iter_id + 1] = cholesky_wrapper(
            rot_cov + rot_cov.det()[:, None, None] ** 0.25 * (self.acg_dispersion * eye_4)
        )
