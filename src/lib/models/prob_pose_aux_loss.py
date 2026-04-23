from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import torch
import torch.nn as nn
import torch.nn.functional as F

from grasp_kpts import GraspKpts3d
from models.monte_carlo_pose_loss import MonteCarloPoseLoss
from models.utils import _transpose_and_gather_feat
from third_party.epropnp.pnp import (
    AdaptiveHuberPnPCost,
    EProPnP6DoF,
    LMSolver,
    PerspectiveCamera,
    RSLMSolver,
)


def _sqrt_positive_part(x):
    ret = torch.zeros_like(x)
    positive_mask = x > 0
    ret[positive_mask] = torch.sqrt(x[positive_mask])
    return ret


def matrix_to_quaternion(matrix):
    if matrix.size(-1) != 3 or matrix.size(-2) != 3:
        raise ValueError("Invalid rotation matrix shape {}.".format(matrix.shape))

    batch_dim = matrix.shape[:-2]
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = torch.unbind(
        matrix.reshape(batch_dim + (9,)), dim=-1
    )

    q_abs = _sqrt_positive_part(
        torch.stack([
            1.0 + m00 + m11 + m22,
            1.0 + m00 - m11 - m22,
            1.0 - m00 + m11 - m22,
            1.0 - m00 - m11 + m22,
        ], dim=-1)
    )
    quat_by_rijk = torch.stack([
        torch.stack([q_abs[..., 0] ** 2, m21 - m12, m02 - m20, m10 - m01], dim=-1),
        torch.stack([m21 - m12, q_abs[..., 1] ** 2, m10 + m01, m02 + m20], dim=-1),
        torch.stack([m02 - m20, m10 + m01, q_abs[..., 2] ** 2, m12 + m21], dim=-1),
        torch.stack([m10 - m01, m20 + m02, m21 + m12, q_abs[..., 3] ** 2], dim=-1),
    ], dim=-2)
    flr = torch.tensor(0.1, dtype=q_abs.dtype, device=q_abs.device)
    quat_candidates = quat_by_rijk / (2.0 * q_abs[..., None].max(flr))
    one_hot = F.one_hot(q_abs.argmax(dim=-1), num_classes=4) > 0.5
    return quat_candidates[one_hot, :].reshape(batch_dim + (4,))


class ProbPoseAuxLoss(nn.Module):
    def __init__(self, opt):
        super(ProbPoseAuxLoss, self).__init__()
        self.output_res = opt.output_res
        self.ori_num = opt.ori_num
        if hasattr(opt, 'num_grasp_kpts'):
            self.num_kpts = opt.num_grasp_kpts
        else:
            self.num_kpts = opt.heads['kpts_center_offset'] // (2 * self.ori_num)
        self.kpt_type = opt.kpt_type
        self.scale_kpts_mode = opt.scale_kpts_mode
        self.scale_coeff_k = float(opt.scale_coeff_k)
        self.open_width_canonical = opt.open_width_canonical
        self.min_open_width = opt.min_open_width
        self.max_pose_grasps = max(1, int(getattr(opt, 'prob_pose_max_grasps', 4)))
        self.target_mode = getattr(opt, 'prob_pose_target_mode', 'first')
        self.target_mode_to_id = {
            'first': 0,
            'random': 1,
            'nearest_cost': 2,
            'nearest_conf': 3,
        }
        if self.target_mode not in self.target_mode_to_id:
            raise ValueError("Unsupported prob_pose_target_mode: {}".format(self.target_mode))
        self.target_mode_id = self.target_mode_to_id[self.target_mode]
        self.target_topk = max(1, int(getattr(opt, 'prob_pose_target_topk', 4)))
        self.target_conf_min = max(
            float(getattr(opt, 'prob_pose_target_conf_min', 0.05)), 1e-6
        )
        self.loss_soft_cap = float(getattr(opt, 'prob_pose_soft_cap', 5.0))
        self.max_cost_mean = float(getattr(opt, 'prob_pose_max_cost_mean', 3.0))
        self.max_raw_loss_abs = 20.0
        self.logweight_clip = float(getattr(opt, 'prob_pose_logweight_clip', 10.0))

        unit_kpts_3d = torch.tensor(
            GraspKpts3d(open_width=1.0, kpt_type=self.kpt_type).get_local_vertices(),
            dtype=torch.float32,
        )
        self.register_buffer('unit_kpts_3d', unit_kpts_3d)

        # Keep a local-debug profile that fits 4GB-class GPUs.
        self.epropnp = EProPnP6DoF(
            mc_samples=8,
            num_iter=1,
            solver=LMSolver(
                dof=6,
                num_iter=2,
                init_solver=RSLMSolver(
                    dof=6,
                    num_points=self.num_kpts,
                    num_proposals=1,
                    num_iter=1,
                ),
            ),
            acg_mle_iter=1,
        )
        self.pose_loss = MonteCarloPoseLoss()

    def _select_orientation_offsets(self, kpts_tensor, ori_clses):
        batch_size, max_grasps = ori_clses.shape
        kpts_tensor = kpts_tensor.view(batch_size, max_grasps, self.ori_num, self.num_kpts, 2)
        gather_index = ori_clses.view(batch_size, max_grasps, 1, 1, 1).expand(
            batch_size, max_grasps, 1, self.num_kpts, 2
        )
        return kpts_tensor.gather(2, gather_index).squeeze(2)

    def _output_to_image_coords(self, coords, center, scale):
        if scale.dim() == 1:
            scale = scale.unsqueeze(-1)
        return (
            (coords - (self.output_res * 0.5))
            * (scale.unsqueeze(1) / float(self.output_res))
            + center.unsqueeze(1)
        )

    def _get_projected_width(self, batch, ori_clses):
        width = batch['w'].gather(2, ori_clses.unsqueeze(2)).squeeze(2)
        if self.scale_kpts_mode:
            scale = batch['scales'].gather(2, ori_clses.unsqueeze(2)).squeeze(2)
            proj_width = scale * width * self.scale_coeff_k
            norm_factor = scale.detach().mean()
        elif self.open_width_canonical is not None:
            proj_width = torch.full_like(width, float(self.open_width_canonical))
            norm_factor = proj_width.detach().mean()
        elif self.min_open_width is not None:
            proj_width = torch.clamp(width, min=float(self.min_open_width))
            norm_factor = proj_width.detach().mean()
        else:
            proj_width = width
            norm_factor = proj_width.detach().mean()
        proj_width = torch.nan_to_num(proj_width, nan=0.0, posinf=0.0, neginf=0.0)
        proj_width = proj_width.clamp(min=1e-4, max=10.0)
        return proj_width, norm_factor.clamp(min=1e-6, max=10.0)

    def _zero_loss(self, reg_map, kpts_center_output):
        return reg_map.sum() * 0 if reg_map is not None else kpts_center_output.sum() * 0

    def _zero_stats(self, zero, *values):
        return tuple(zero.detach() + float(value) for value in values)

    def _gather_orientation_scalar(self, feat_map, inds, ori_clses):
        feat = _transpose_and_gather_feat(feat_map, inds)
        return feat.gather(2, ori_clses.unsqueeze(2)).squeeze(2)

    def _select_target_indices(
        self, valid_indices, target_cost=None, target_conf_quality=None
    ):
        valid_total = valid_indices.sum()
        valid_total_int = int(valid_total.item())
        cost_zero = valid_total.detach().float() * 0.0
        if valid_total_int == 0:
            return (
                valid_indices,
                valid_total,
                valid_total,
                cost_zero,
                cost_zero,
                cost_zero,
            )

        valid_coords = valid_indices.nonzero(as_tuple=False)
        if self.target_mode == 'first':
            selected_count_int = min(valid_total_int, self.max_pose_grasps)
            selected_coords = valid_coords[:selected_count_int]
            select_cost_mean = cost_zero
            geom_cost_mean = cost_zero
            conf_quality_mean = cost_zero
        elif self.target_mode == 'random':
            selected_count_int = min(valid_total_int, self.max_pose_grasps)
            perm = torch.randperm(valid_total_int, device=valid_coords.device)
            selected_coords = valid_coords[perm[:selected_count_int]]
            select_cost_mean = cost_zero
            geom_cost_mean = cost_zero
            conf_quality_mean = cost_zero
        elif self.target_mode == 'nearest_cost':
            if target_cost is None:
                raise ValueError("nearest_cost target selection requires target_cost")
            valid_cost = target_cost[valid_indices].detach()
            valid_cost = torch.nan_to_num(
                valid_cost, nan=1e6, posinf=1e6, neginf=1e6
            )
            topk_count = min(valid_total_int, self.target_topk)
            selected_count_int = min(topk_count, self.max_pose_grasps)
            _, order = torch.topk(valid_cost, k=topk_count, largest=False)
            selected_order = order[:selected_count_int]
            selected_coords = valid_coords[selected_order]
            select_cost_mean = valid_cost[selected_order].mean()
            geom_cost_mean = select_cost_mean
            conf_quality_mean = cost_zero
        else:
            if target_cost is None:
                raise ValueError("nearest_conf target selection requires target_cost")
            if target_conf_quality is None:
                raise ValueError(
                    "nearest_conf target selection requires target_conf_quality"
                )
            valid_cost = target_cost[valid_indices].detach()
            valid_cost = torch.nan_to_num(
                valid_cost, nan=1e6, posinf=1e6, neginf=1e6
            )
            valid_conf_quality = target_conf_quality[valid_indices].detach()
            valid_conf_quality = torch.nan_to_num(
                valid_conf_quality, nan=0.0, posinf=1.0, neginf=0.0
            ).clamp(min=0.0, max=1.0)
            topk_count = min(valid_total_int, self.target_topk)
            _, order = torch.topk(valid_cost, k=topk_count, largest=False)
            pool_cost = valid_cost[order]
            pool_conf_quality = valid_conf_quality[order]
            pool_select_score = pool_cost / pool_conf_quality.clamp(
                min=self.target_conf_min
            )
            selected_count_int = min(topk_count, self.max_pose_grasps)
            _, refined_order = torch.topk(
                pool_select_score, k=selected_count_int, largest=False
            )
            selected_order = order[refined_order]
            selected_coords = valid_coords[selected_order]
            select_cost_mean = pool_select_score[refined_order].mean()
            geom_cost_mean = valid_cost[selected_order].mean()
            conf_quality_mean = valid_conf_quality[selected_order].mean()

        selected_indices = torch.zeros_like(valid_indices)
        if selected_coords.numel() > 0:
            selected_indices[selected_coords[:, 0], selected_coords[:, 1]] = True
        selected_count = selected_indices.sum()
        return (
            selected_indices,
            valid_total,
            selected_count,
            select_cost_mean,
            geom_cost_mean,
            conf_quality_mean,
        )

    def _compute_detached_keypoint_cost(
        self, kpt_pred_img, ct_int, ori_clses, pose_centers, pose_scales, batch
    ):
        if 'reg' in batch:
            reg_gt = batch['reg'].float()
        else:
            reg_gt = torch.zeros_like(ct_int)
        center_gt = ct_int + reg_gt

        target_offsets = self._select_orientation_offsets(
            batch['kpts_center_offset'].float(), ori_clses
        )
        target_mask = self._select_orientation_offsets(
            batch['kpts_center_mask'].float(), ori_clses
        ).float()
        kpt_gt_out = center_gt.unsqueeze(2) + target_offsets
        kpt_gt_img = self._output_to_image_coords(kpt_gt_out, pose_centers, pose_scales)

        coord_valid_count = target_mask.sum(dim=(2, 3))
        keypoint_cost = (
            torch.abs(kpt_pred_img - kpt_gt_img) * target_mask
        ).sum(dim=(2, 3)) / (coord_valid_count + 1e-4)
        keypoint_cost = torch.where(
            coord_valid_count > 0,
            keypoint_cost,
            keypoint_cost.new_full(keypoint_cost.shape, 1e6),
        )
        return torch.nan_to_num(
            keypoint_cost.detach(), nan=1e6, posinf=1e6, neginf=1e6
        )

    def forward(self, reg_map, kpts_center_output, batch, conf_map=None):
        ori_clses = batch['ori_clses'].long()
        ct_int_x = (batch['ind'] % self.output_res).float()
        ct_int_y = torch.div(batch['ind'], self.output_res, rounding_mode='floor').float()
        ct_int = torch.stack([ct_int_x, ct_int_y], dim=2)

        if reg_map is not None and 'reg' in batch:
            reg_pred = _transpose_and_gather_feat(reg_map, batch['ind'])
        else:
            reg_pred = torch.zeros_like(ct_int)
        center_pred = ct_int + reg_pred

        kpts_center_pred = _transpose_and_gather_feat(kpts_center_output, batch['ind'])
        pred_offsets = self._select_orientation_offsets(kpts_center_pred, ori_clses)
        kpt_pred_out = center_pred.unsqueeze(2) + pred_offsets

        pose_loss_valid = batch['pose_loss_valid'].float().view(-1, 1)
        valid_mask = batch['reg_mask'].float() * batch['grasp_pose_mask'].float() * pose_loss_valid
        valid_indices = valid_mask > 0
        valid_count = valid_indices.sum()
        if valid_count.item() == 0:
            zero = self._zero_loss(reg_map, kpts_center_output)
            stats = self._zero_stats(
                zero,
                0.0,  # valid_count
                0.0,  # cost_mean
                0.0,  # raw_loss
                0.0,  # high_cost_rate
                1.0,  # skip_rate
                1.0,  # no_valid_rate
                0.0,  # invalid_raw_rate
                0.0,  # too_large_raw_rate
                0.0,  # target_valid_total
                0.0,  # target_selected_count
                0.0,  # target_select_cost_mean
                0.0,  # target_geom_cost_mean
                0.0,  # target_conf_quality_mean
                self.target_mode_id,  # target_mode_id
            )
            return (zero,) + stats

        pose_centers = batch['pose_loss_meta_c'].float()
        pose_scales = batch['pose_loss_meta_s'].float().view(-1, 1)
        kpt_pred_img = self._output_to_image_coords(kpt_pred_out, pose_centers, pose_scales)

        target_geom_cost = None
        if self.target_mode in ('nearest_cost', 'nearest_conf'):
            target_geom_cost = self._compute_detached_keypoint_cost(
                kpt_pred_img, ct_int, ori_clses, pose_centers, pose_scales, batch
            )
        target_conf_quality = None
        if self.target_mode == 'nearest_conf':
            if conf_map is None:
                raise ValueError("nearest_conf target selection requires conf_map")
            conf_pred = self._gather_orientation_scalar(conf_map, batch['ind'], ori_clses)
            target_conf_quality = torch.sigmoid(-conf_pred)
            target_conf_quality = torch.nan_to_num(
                target_conf_quality, nan=0.0, posinf=1.0, neginf=0.0
            ).detach().clamp(min=0.0, max=1.0)
        valid_indices, target_valid_total, target_selected_count, \
            target_select_cost_mean, target_geom_cost_mean, \
            target_conf_quality_mean = self._select_target_indices(
                valid_indices, target_geom_cost, target_conf_quality
            )
        valid_count = target_selected_count

        kpt_pred_img = kpt_pred_img[valid_indices]
        pose_gt_mat = batch['grasp_pose_cam'].float()[valid_indices]
        cam_intrinsic = batch['camera_intrinsic'].float()
        cam_intrinsic = cam_intrinsic.unsqueeze(1).expand(-1, batch['ind'].size(1), -1, -1)[valid_indices]
        img_hw = batch['pose_loss_img_hw'].float()
        img_hw = img_hw.unsqueeze(1).expand(-1, batch['ind'].size(1), -1)[valid_indices]

        proj_width, norm_factor = self._get_projected_width(batch, ori_clses)
        proj_width = proj_width[valid_indices].float()
        x3d = self.unit_kpts_3d.unsqueeze(0) * proj_width.view(-1, 1, 1)

        pose_gt_rot = pose_gt_mat[:, :3, :3]
        pose_gt_quat = F.normalize(matrix_to_quaternion(pose_gt_rot), dim=-1)
        pose_gt = torch.cat([pose_gt_mat[:, :3, 3], pose_gt_quat], dim=1)

        kpt_pred_img = torch.nan_to_num(kpt_pred_img, nan=0.0, posinf=0.0, neginf=0.0)
        x3d = torch.nan_to_num(x3d, nan=0.0, posinf=0.0, neginf=0.0)
        pose_gt = torch.nan_to_num(pose_gt, nan=0.0, posinf=0.0, neginf=0.0)
        cam_intrinsic = torch.nan_to_num(cam_intrinsic, nan=0.0, posinf=0.0, neginf=0.0)
        img_hw = torch.nan_to_num(img_hw, nan=0.0, posinf=0.0, neginf=0.0)

        w2d = torch.ones_like(kpt_pred_img)
        camera = PerspectiveCamera(
            cam_mats=cam_intrinsic,
            z_min=0.01,
            img_shape=img_hw,
        )
        cost_fun = AdaptiveHuberPnPCost(relative_delta=0.1)
        cost_fun.set_param(kpt_pred_img, w2d)

        _, _, _, _, pose_sample_logweights, cost_tgt = self.epropnp.monte_carlo_forward(
            x3d,
            kpt_pred_img,
            w2d,
            camera,
            cost_fun,
            pose_init=pose_gt,
            force_init_solve=True,
            # T3.1 only needs the Monte Carlo samples / weights and target cost.
            # Skip the extra Gauss-Newton "pose_opt_plus" branch for now to keep
            # the clean prototype focused and avoid solver-side shape coupling.
            with_pose_opt_plus=False,
        )

        pose_sample_logweights = torch.nan_to_num(
            pose_sample_logweights, nan=0.0, posinf=0.0, neginf=0.0
        ).clamp(min=-self.logweight_clip, max=self.logweight_clip)
        cost_tgt = torch.nan_to_num(
            cost_tgt, nan=0.0, posinf=0.0, neginf=0.0
        ).clamp(min=0.0, max=30.0)
        cost_tgt_raw_mean = cost_tgt.mean().detach()
        high_cost_rate = (
            cost_tgt_raw_mean > self.max_cost_mean
        ).to(dtype=cost_tgt_raw_mean.dtype) if self.max_cost_mean > 0 else cost_tgt_raw_mean * 0
        cost_tgt = (cost_tgt - cost_tgt.mean()) / (cost_tgt.std(unbiased=False) + 1e-6)
        # For the clean local prototype, keep the learning signal on the
        # differentiable Monte Carlo logweights and use the target cost as a
        # detached baseline to reduce backward graph size.
        cost_tgt = cost_tgt.detach()

        raw_loss = self.pose_loss(pose_sample_logweights, cost_tgt, norm_factor)
        raw_loss_detached = raw_loss.detach()
        raw_loss_is_finite = torch.isfinite(raw_loss_detached)
        invalid_raw = not raw_loss_is_finite.item()
        too_large_raw = (
            raw_loss_is_finite.item()
            and raw_loss_detached.abs().item() > self.max_raw_loss_abs
        )
        if invalid_raw:
            zero = self._zero_loss(reg_map, kpts_center_output)
            valid_count_tensor = valid_count.to(dtype=zero.dtype)
            raw_loss_stat = torch.nan_to_num(
                raw_loss_detached,
                nan=0.0,
                posinf=self.max_raw_loss_abs,
                neginf=-self.max_raw_loss_abs,
            )
            stats = (
                valid_count_tensor.detach(),
                cost_tgt_raw_mean,
                raw_loss_stat,
                high_cost_rate.detach(),
            ) + self._zero_stats(
                zero,
                1.0,  # skip_rate
                0.0,  # no_valid_rate
                1.0,  # invalid_raw_rate
                0.0,  # too_large_raw_rate
            ) + (
                target_valid_total.to(dtype=zero.dtype).detach(),
                target_selected_count.to(dtype=zero.dtype).detach(),
                target_select_cost_mean.to(dtype=zero.dtype).detach(),
                target_geom_cost_mean.to(dtype=zero.dtype).detach(),
                target_conf_quality_mean.to(dtype=zero.dtype).detach(),
                zero.detach() + float(self.target_mode_id),
            )
            return (zero,) + stats

        # The reference Monte Carlo pose term is a log-likelihood-style value
        # and can become negative. In this local auxiliary branch we do not yet
        # include the extra pose_opt_plus translation/rotation losses used by
        # KGN-Pro, so optimize a bounded non-negative magnitude proxy while
        # keeping the raw signed value for diagnostics.
        loss = raw_loss.abs()
        if self.loss_soft_cap > 0:
            loss = self.loss_soft_cap * torch.tanh(loss / self.loss_soft_cap)
        valid_count_tensor = valid_count.to(dtype=loss.dtype)
        zero_stat = loss.detach() * 0
        target_valid_total_tensor = target_valid_total.to(dtype=loss.dtype).detach()
        target_selected_count_tensor = target_selected_count.to(dtype=loss.dtype).detach()
        target_select_cost_mean = target_select_cost_mean.to(dtype=loss.dtype).detach()
        target_geom_cost_mean = target_geom_cost_mean.to(dtype=loss.dtype).detach()
        target_conf_quality_mean = target_conf_quality_mean.to(dtype=loss.dtype).detach()
        return (
            loss,
            valid_count_tensor.detach(),
            cost_tgt_raw_mean,
            raw_loss_detached,
            high_cost_rate.detach(),
            zero_stat,  # skip_rate
            zero_stat,  # no_valid_rate
            zero_stat,  # invalid_raw_rate
            zero_stat + (1.0 if too_large_raw else 0.0),
            target_valid_total_tensor,
            target_selected_count_tensor,
            target_select_cost_mean,
            target_geom_cost_mean,
            target_conf_quality_mean,
            zero_stat + float(self.target_mode_id),
        )
