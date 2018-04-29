from unittest import TestCase

from monte_carlo import *


class MetropTest(TestCase):

    def test_mean(self):
        met = make_metropolis(1, lambda x: 1)
        met.init_sampler(0.1)  # initialize with start value
        sample = met.sample(1000)  # generate 1000 samples
        self.assertAlmostEqual(0.5, np.mean(sample), 1)

    def test_uniform(self):
        pdf = lambda x: np.sin(10 * x) ** 2
        met = make_metropolis(1, pdf)  # 1 dimensional
        met.init_sampler(0.1)  # initialize with start value
        sample = met.sample(1000)  # generate 1000 samples
        self.assertEqual(sample.shape, (1000, 1))

    def test_local(self):
        ndim = 2
        delta = 0.01

        def local(state):
            base = np.maximum(np.zeros(ndim), state - delta / 2)
            base_capped = np.minimum(base, np.ones(ndim) - delta)
            return base_capped + np.random.rand() * delta

        dist = make_dist_vect(ndim, lambda x, y: np.sin(10 * x * y) ** 2)
        met = make_metropolis(ndim, dist.pdf, local)  # 1 dimensional
        met.init_sampler([0.1, 0.1])  # initialize with start value
        sample = met.sample(1000)  # generate 1000 samples
        self.assertEqual(sample.shape, (1000, 2))


class AdaptiveMetTest(TestCase):
    def test_mean(self):
        proposal_dist = Gaussian(1)
        met = AdaptiveMetropolisUpdate(
            1, lambda x: (0 < x) * (x < 1), proposal_dist, 10, lambda t: t<100)
        met.init_sampler(0.1)  # initialize with start value
        sample = met.sample(1000)  # generate 1000 samples
        self.assertAlmostEqual(0.5, np.mean(sample), 0)


class HamiltonTest(TestCase):

    def test_gauss(self):
        s = 1
        # hamilton monte carlo
        density = Gaussian(1)
        momentum_dist = densities.Gaussian(1, scale=1)
        hmcm = HamiltonianUpdate(density, momentum_dist, steps=10, step_size=1)
        hmcm.init_sampler(0., get_info=True)
        res = hmcm.sample(100)
        self.assertEqual((100, 1), res.shape)


class HamiltonDualAvTest(TestCase):

    def test_gauss(self):
        s = 1
        dh_dq = lambda q: q
        pdf = lambda x: np.exp(-x ** 2 / 2 / s ** 2) / np.sqrt(
            2 * np.pi * s ** 2)
        # hamilton monte carlo
        density = densities.make_dist(1, pdf, pdf_gradient=dh_dq)
        momentum_dist = densities.Gaussian(1, scale=1)
        hmcm = DualAveragingHMCUpdate(density, momentum_dist, 1, lambda t: t < 10)
        hmcm.init_sampler(0., get_info=True)
        res = hmcm.sample(100)
        self.assertEqual((100, 1), res.shape)


class HamiltonNUTSTest(TestCase):

    def test_gauss(self):
        s = 1
        dh_dq = lambda q: q
        pdf = lambda x: np.exp(-x ** 2 / 2 / s ** 2) / np.sqrt(
            2 * np.pi * s ** 2)
        # hamilton monte carlo
        density = densities.make_dist(1, pdf, pdf_gradient=dh_dq)
        momentum_dist = densities.Gaussian(1, scale=1)
        hmcm = NUTSUpdate(density, momentum_dist, lambda t: t < 10)
        hmcm.init_sampler(0., get_info=True)
        res = hmcm.sample(100)
        self.assertEqual((100, 1), res.shape)
