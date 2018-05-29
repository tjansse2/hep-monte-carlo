import sys
import Sherpa
from ..density import Density
from ..util import interpret_array
import numpy as np


# e+ e- -> q qbar
class ee_qq(Density):
    def __init__(self, E_CM, mapping=None):
        ndim = 8
        self.conversion = 0.389379*1e9  # convert to picobarn
        self.nfinal = 2  # number of final state particles

        super().__init__(ndim, False)

        self.mapping = mapping

        self.E_CM = E_CM

        self.Generator = Sherpa.Sherpa()
        self.Generator.InitializeTheRun(3, [''.encode('ascii'), 'INIT_ONLY=2'.encode('ascii'), 'OUTPUT=0'.encode('ascii')])
        self.Process = Sherpa.MEProcess(self.Generator)

        # Incoming flavors must be added first!
        self.Process.AddInFlav(11)
        self.Process.AddInFlav(-11)
        self.Process.AddOutFlav(1)
        self.Process.AddOutFlav(-1)
        self.Process.Initialize()

        self.Process.SetMomentum(0, E_CM/2., 0., 0., E_CM/2.)
        self.Process.SetMomentum(1, E_CM/2., 0., 0., -E_CM/2.)

    # The first momentum is xs[0:4]
    # The second momentum is xs[4:8]
    def pdf(self, xs):
        xs = interpret_array(xs, self.ndim)
        if self.mapping:
            xs = self.mapping(xs, self.E_CM, 2)
        ndim = xs.shape[1]

        if ndim != self.ndim:
            raise RuntimeWarning("Mismatching dimensions.")

        p1 = xs[:, 0:4]
        p2 = xs[:, 4:8]

        sample_size = len(xs)
        me = np.empty(sample_size)
        for i in range(sample_size):
            self.Process.SetMomentum(2, p1[i, 0], p1[i, 1], p1[i, 2], p1[i, 3])
            self.Process.SetMomentum(3, p2[i, 0], p2[i, 1], p2[i, 2], p2[i, 3])
            me[i] = self.Process.CSMatrixElement()

        return self.conversion * (2.*np.pi)**(4.-3.*self.nfinal)/(2.*self.E_CM**2) * me
