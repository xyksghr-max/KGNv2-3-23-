"""
Minimal common utilities vendored from EPro-PnP and cleaned for local use.
"""

import torch


def skew(x):
    mat = x.new_zeros(x.shape[:-1] + (3, 3))
    mat[..., [2, 0, 1], [1, 2, 0]] = x
    mat[..., [1, 2, 0], [2, 0, 1]] = -x
    return mat


def quaternion_to_rot_mat(quaternions):
    if quaternions.requires_grad:
        w = quaternions[..., 0].clone()
        i = quaternions[..., 1].clone()
        j = quaternions[..., 2].clone()
        k = quaternions[..., 3].clone()
        rot_mats = torch.stack((
            1 - 2 * (j * j + k * k),     2 * (i * j - k * w),     2 * (i * k + j * w),
                2 * (i * j + k * w), 1 - 2 * (i * i + k * k),     2 * (j * k - i * w),
                2 * (i * k - j * w),     2 * (j * k + i * w), 1 - 2 * (i * i + j * j)), dim=-1,
        ).reshape(quaternions.shape[:-1] + (3, 3))
    else:
        w, v = quaternions.split([1, 3], dim=-1)
        rot_mats = 2 * (w.unsqueeze(-1) * skew(v) + v.unsqueeze(-1) * v.unsqueeze(-2))
        diag = torch.diagonal(rot_mats, dim1=-2, dim2=-1)
        diag += w * w - (v.unsqueeze(-2) @ v.unsqueeze(-1)).squeeze(-1)
    return rot_mats


def yaw_to_rot_mat(yaw):
    sin_yaw = torch.sin(yaw)
    cos_yaw = torch.cos(yaw)
    rot_mats = yaw.new_zeros(yaw.shape + (3, 3))
    rot_mats[..., 0, 0] = cos_yaw
    rot_mats[..., 2, 2] = cos_yaw
    rot_mats[..., 0, 2] = sin_yaw
    rot_mats[..., 2, 0] = -sin_yaw
    rot_mats[..., 1, 1] = 1
    return rot_mats


def evaluate_pnp(x3d, x2d, w2d, pose, camera, cost_fun,
                 out_jacobian=False, out_residual=False, out_cost=False, **kwargs):
    x2d_proj, jac_cam = camera.project(
        x3d, pose, out_jac=(
            out_jacobian.view(x2d.shape[:-1] + (2, out_jacobian.size(-1)))
            if isinstance(out_jacobian, torch.Tensor)
            else out_jacobian), **kwargs)
    residual, cost, jacobian = cost_fun.compute(
        x2d_proj, x2d, w2d, jac_cam=jac_cam,
        out_residual=out_residual,
        out_cost=out_cost,
        out_jacobian=out_jacobian)
    return residual, cost, jacobian


def pnp_normalize(x3d, pose=None, detach_transformation=True):
    offset = torch.mean(
        x3d.detach() if detach_transformation else x3d, dim=-2)
    x3d_norm = x3d - offset.unsqueeze(-2)
    if pose is not None:
        pose_norm = torch.empty_like(pose)
        pose_norm[..., 3:] = pose[..., 3:]
        pose_norm[..., :3] = pose[..., :3] + (
            (yaw_to_rot_mat(pose[..., 3]) if pose.size(-1) == 4
             else quaternion_to_rot_mat(pose[..., 3:])) @ offset.unsqueeze(-1)
        ).squeeze(-1)
    else:
        pose_norm = None
    return offset, x3d_norm, pose_norm


def pnp_denormalize(offset, pose_norm):
    pose = torch.empty_like(pose_norm)
    pose[..., 3:] = pose_norm[..., 3:]
    pose[..., :3] = pose_norm[..., :3] - (
        (yaw_to_rot_mat(pose_norm[..., 3]) if pose_norm.size(-1) == 4
         else quaternion_to_rot_mat(pose_norm[..., 3:])) @ offset.unsqueeze(-1)
    ).squeeze(-1)
    return pose
