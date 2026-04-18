"""
Minimal probability distributions used by EPro-PnP without depending on pyro.
"""

import math
import numpy as np
import torch

from torch.distributions import Gamma, VonMises
from torch.distributions.multivariate_normal import _batch_mahalanobis, _batch_mv, _standard_normal


def _broadcast_shape(*shapes):
    shape = torch.Size()
    for item in shapes:
        shape = torch.broadcast_shapes(shape, torch.Size(item))
    return shape


class MultivariateStudentT(object):
    def __init__(self, df, loc, scale_tril, validate_args=None):
        del validate_args
        self.df = float(df)
        self.loc = loc
        self.scale_tril = scale_tril
        self.event_shape = (loc.size(-1),)
        self.batch_shape = _broadcast_shape(loc.shape[:-1], scale_tril.shape[:-2])

    def sample(self, sample_shape=torch.Size()):
        sample_shape = torch.Size(sample_shape)
        shape = sample_shape + self.batch_shape + self.event_shape
        normal = _standard_normal(shape, dtype=self.loc.dtype, device=self.loc.device)
        scale = self.scale_tril.expand(self.batch_shape + self.scale_tril.shape[-2:])
        loc = self.loc.expand(self.batch_shape + self.event_shape)
        mv_samples = _batch_mv(scale, normal)
        gamma = Gamma(
            torch.full(self.batch_shape, self.df / 2.0, dtype=self.loc.dtype, device=self.loc.device),
            torch.full(self.batch_shape, 0.5, dtype=self.loc.dtype, device=self.loc.device),
        ).rsample(sample_shape)
        denom = torch.sqrt(gamma / self.df).unsqueeze(-1)
        return loc + mv_samples / denom

    def log_prob(self, value):
        batch_shape = _broadcast_shape(value.shape[:-1], self.batch_shape)
        loc = self.loc.expand(batch_shape + self.event_shape)
        scale = self.scale_tril.expand(batch_shape + self.scale_tril.shape[-2:])
        centered = value.expand(batch_shape + self.event_shape) - loc
        mahal = _batch_mahalanobis(scale, centered)
        dim = self.event_shape[0]
        log_det = scale.diagonal(dim1=-2, dim2=-1).log().sum(-1)
        return (
            torch.lgamma(centered.new_tensor((self.df + dim) / 2.0))
            - torch.lgamma(centered.new_tensor(self.df / 2.0))
            - 0.5 * dim * math.log(self.df * math.pi)
            - log_det
            - 0.5 * (self.df + dim) * torch.log1p(mahal / self.df)
        )


class AngularCentralGaussian(object):
    def __init__(self, scale_tril, validate_args=None, eps=1e-6):
        del validate_args
        q = scale_tril.size(-1)
        assert q > 1
        assert scale_tril.shape[-2:] == (q, q)
        self.scale_tril = scale_tril
        self.q = q
        self.area = 2 * math.pi ** (0.5 * q) / math.gamma(0.5 * q)
        self.eps = eps
        self.batch_shape = scale_tril.shape[:-2]
        self.event_shape = (q,)

    def log_prob(self, value):
        batch_shape = _broadcast_shape(value.shape[:-1], self.batch_shape)
        scale = self.scale_tril.expand(batch_shape + self.scale_tril.shape[-2:])
        value = value.expand(batch_shape + self.event_shape)
        mahal = _batch_mahalanobis(scale, value)
        half_log_det = scale.diagonal(dim1=-2, dim2=-1).log().sum(-1)
        return mahal.log() * (-self.q / 2.0) - half_log_det - math.log(self.area)

    def sample(self, sample_shape=torch.Size()):
        sample_shape = torch.Size(sample_shape)
        shape = sample_shape + self.batch_shape + self.event_shape
        normal = _standard_normal(shape, dtype=self.scale_tril.dtype, device=self.scale_tril.device)
        gaussian_samples = _batch_mv(
            self.scale_tril.expand(self.batch_shape + self.scale_tril.shape[-2:]),
            normal,
        )
        gaussian_norm = gaussian_samples.norm(dim=-1, keepdim=True)
        samples = gaussian_samples / gaussian_norm.clamp(min=self.eps)
        invalid_mask = gaussian_norm.squeeze(-1) < self.eps
        if invalid_mask.any():
            fill = samples.new_tensor([1.] + [0. for _ in range(self.q - 1)])
            samples[invalid_mask] = fill
        return samples


class VonMisesUniformMix(VonMises):
    def __init__(self, loc, concentration, uniform_mix=0.25, **kwargs):
        super(VonMisesUniformMix, self).__init__(loc, concentration, **kwargs)
        self.uniform_mix = uniform_mix

    @torch.no_grad()
    def sample(self, sample_shape=torch.Size()):
        sample_shape = torch.Size(sample_shape)
        assert len(sample_shape) == 1
        x = np.empty(tuple(self._extended_shape(sample_shape)), dtype=np.float32)
        uniform_samples = round(sample_shape[0] * self.uniform_mix)
        von_mises_samples = sample_shape[0] - uniform_samples
        x[:uniform_samples] = np.random.uniform(
            -math.pi, math.pi, size=tuple(self._extended_shape((uniform_samples,))))
        x[uniform_samples:] = np.random.vonmises(
            self.loc.cpu().numpy(), self.concentration.cpu().numpy(),
            size=tuple(self._extended_shape((von_mises_samples,))))
        return torch.from_numpy(x).to(self.loc.device)

    def log_prob(self, value):
        von_mises_log_prob = super(VonMisesUniformMix, self).log_prob(value) + np.log(1 - self.uniform_mix)
        return torch.logaddexp(
            von_mises_log_prob,
            torch.full_like(von_mises_log_prob, math.log(self.uniform_mix / (2 * math.pi))))
