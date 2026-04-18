"""
Monte Carlo pose loss vendored from KGN-Pro and kept as a self-contained module.
"""

import torch
import torch.nn as nn


class MonteCarloPoseLoss(nn.Module):
    def __init__(self, init_norm_factor=1.0, momentum=0.01):
        super(MonteCarloPoseLoss, self).__init__()
        self.register_buffer('norm_factor', torch.tensor(init_norm_factor, dtype=torch.float))
        self.momentum = momentum

    def forward(self, pose_sample_logweights, cost_target, norm_factor):
        if self.training:
            with torch.no_grad():
                self.norm_factor.mul_(1 - self.momentum).add_(self.momentum * norm_factor)

        max_logweights = pose_sample_logweights.max(dim=0, keepdim=True).values
        loss_pred = torch.logsumexp(pose_sample_logweights - max_logweights, dim=0) + max_logweights.squeeze(0)
        loss_pose = cost_target + loss_pred
        loss_pose[torch.isnan(loss_pose)] = 0
        return loss_pose.mean() / self.norm_factor.clamp(min=1e-6)
