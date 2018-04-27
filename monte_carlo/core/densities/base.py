import numpy as np

from ..util import interpret_array


class Density(object):

    def __init__(self, ndim, is_symmetric=None):
        self.ndim = ndim
        self.is_symmetric=is_symmetric

    def __call__(self, *xs):
        try:
            return self.pdf(np.stack(xs, axis=1))
        except np.AxisError:
            # xs must be numbers
            return self.pdf(np.stack(xs, axis=0))

    def pot(self, xs):
        with np.errstate(divide='ignore'):
            pot = -np.log(self.pdf(xs))

        pot[np.isnan(pot)] = np.inf
        return pot

    def pot_gradient(self, xs):
        xs = interpret_array(xs, self.ndim)
        pdf = self.pdf(xs)[:, np.newaxis]
        res = np.empty(xs.shape)

        # compute where pdf is != 0
        nonzero = np.all(xs != 0, axis=1)
        pdf_grad = self.pdf_gradient(xs[nonzero])
        res[nonzero] = -pdf_grad / pdf[nonzero]

        # set others to inf
        res[np.logical_not(nonzero)] = np.inf

        return res

    def pdf(self, xs):
        raise NotImplementedError()

    def pdf_gradient(self, xs):
        raise NotImplementedError()


class Distribution(Density):

    def proposal(self):
        return self.rvs(1)[0]

    def pdf(self, xs):
        raise NotImplementedError()

    def pdf_gradient(self, xs):
        raise NotImplementedError()

    def rvs(self, sample_count):
        raise NotImplementedError()


def make_dist(ndim, pdf, sampling, pdf_gradient=None):
    dist = Distribution(ndim)
    dist.pdf = lambda xs: pdf(xs).flatten()
    dist.rvs = lambda count: interpret_array(sampling(count), ndim)
    if pdf_gradient is not None:
        dist.pdf_gradient = pdf_gradient
    return dist


def make_dist_vect(ndim, pdf_vect, sampling):
    dist = Distribution(ndim)
    dist.__call__ = lambda *xs: pdf_vect(*xs).flatten()
    dist.pdf = lambda xs: pdf_vect(*xs.transpose()).flatten()
    dist.rvs = lambda count: interpret_array(sampling(count), ndim)
    return dist
