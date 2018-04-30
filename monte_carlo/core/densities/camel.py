from .base import Density
from scipy.stats import multivariate_normal
import numpy as np

from ..util import interpret_array, hypercube_bounded


class UnconstrainedCamel(Density):
    """
    sum of two gaussians on a [0, 1] hypercube
    """
    def __init__(self, ndim, mu_a=1/3, mu_b=2/3, a=0.1):
        super().__init__(ndim)
        self.mu_a = mu_a
        self.mu_b = mu_b
        self.cov = a**2/2
    
    def pdf(self, xs):
        xs = interpret_array(xs, self.ndim)
        ndim = xs.shape[1]

        if ndim != self.ndim:
            raise RuntimeWarning("Mismatching dimensions.")

        mu_a = ndim*[self.mu_a]
        mu_b = ndim*[self.mu_b]

        pdf_a = np.atleast_1d(
            multivariate_normal.pdf(xs, mean=mu_a, cov=self.cov))
        pdf_b = np.atleast_1d(
            multivariate_normal.pdf(xs, mean=mu_b, cov=self.cov))
        return (pdf_a + pdf_b).flatten() / 2
    
    def pdf_gradient(self, xs):
        xs = interpret_array(xs, self.ndim)
        ndim = xs.shape[1]

        if ndim != self.ndim:
            raise RuntimeWarning("Mismatching dimensions.")

        mu_a = ndim * [self.mu_a]
        mu_b = ndim * [self.mu_b]
        pdf_a = np.atleast_1d(
            multivariate_normal.pdf(xs, mean=mu_a, cov=self.cov))
        pdf_b = np.atleast_1d(
            multivariate_normal.pdf(xs, mean=mu_b, cov=self.cov))
        return ((-xs + self.mu_a) / self.cov * pdf_a[:, np.newaxis] +
                (-xs + self.mu_b) / self.cov * pdf_b[:, np.newaxis]) / 2


class Camel(UnconstrainedCamel):
    """
    sum of two gaussians on a [0, 1] hypercube
    """
    @hypercube_bounded(1, self_has_ndim=True)
    def pdf(self, xs):
        return super().pdf(xs).flatten()

    def pdf_gradient(self, xs):
        xs = interpret_array(xs, self.ndim)

        in_bounds = np.all((0 < xs) * (xs < 1), axis=1)

        res = np.empty(xs.shape)
        res[in_bounds] = super().pdf_gradient(xs[in_bounds])
        res[np.logical_not(in_bounds)] = 0

        return res