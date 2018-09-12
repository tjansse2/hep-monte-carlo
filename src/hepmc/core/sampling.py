"""
Module containing several sampling methods and sampling structures used
in Monte Carlo integration and sampling techniques.

The core goal of sampling is to generate a sample of points distributed
according to a general (unnormalized) distribution function about which
little or nothing is known.
"""

from typing import Optional, Callable
import numpy as np
from .util import interpret_array, effective_sample_size, bin_wise_chi2
from .sample_plotting import plot1d, plot2d
from ..core.density import Density

import os
import time
import json


#def _set(*args):
#    return all(arg is not None for arg in args)


class Sample(object):
    """A general sample class.

    A sample contains 2-dimensional data (shape: (n_samples, n_dimensions)) and 
    can contain optional information like target pdf values. It always provides 
    a weight member. If the weights haven't been filled by the sampler, a normalized 
    vector containing the same value in every entry will be returned.
    """
    def __init__(self, data: any, target: Optional[Density] = None, pdf: Optional[any] = None, pot: Optional[any] = None, weights: Optional[any] = None) -> None:
        """
        Parameters
        ----------
        data : ndarray
            2D array containing the samples
            first dimenion indices the individual samples
            second dimension indices the phase space dimensions
        target : Density, optional
            the target density to which the sample corresponds
        pdf : ndarray, optional
            values of target pdf evaluated at data points
        pot : ndarray, optional
            values of target potential (minus log pdf) evaluated at data points
        weights : ndarray, optional
            1D array containing the weights
        """
        # check that arrays are actually numpy arrays and have the right dimension
        try:
            if data.ndim != 2:
                raise RuntimeWarning("The data array is expected to have 2 dimensions.")
        except AttributeError:
            raise RuntimeWarning("'data' has to be a numpy array.")
        if weights is not None:
            try:
                if weights.ndim != 1:
                    raise RuntimeWarning("The weights array is expected to have 1 dimension.")
            except AttributeError:
                raise RuntimeWarning("'weights' has to be a numpy array.")

        self._data = data
        self._target = target
        self._pdf = pdf
        self._pot = pot
        self._weights = weights

        self._bin_wise_chi2 = None
        self._effective_sample_size = None
        self._variance = None
        self._mean = None

        self._sample_info = [
            ('size', 'data (size)', '%s'),
            ('mean', 'mean', '%s'),
            ('variance', 'variance', '%s'),
            ('bin_wise_chi2', 'bin-wise chi^2', '%.4g, p=%.4g, N=%d'),
            ('effective_sample_size', 'effective sample size', '%s'),
        ]

    # PROPERTIES
    @property
    def data(self):
        return self._data

    @property
    def target(self):
        return self._target

    @property
    def pdf(self):
        if self._pdf is None and self._target is not None:
            print("PDF values have not been set but will be calculated now...")
            self._pdf = self._target.pdf(self._data)
        return self._pdf

    @property
    def pot(self):
        if self._pot is None and self._target is not None:
            print("Potential values have not been set but will be calculated now...")
            self._pot = self._target.pot(self._data)
        return self._pot

    @property
    def weights(self):
        if self._weights is None:
            self._weights = np.full(self.size, 1./self.size)
        return self._weights

    @property
    def size(self):
        return self.data.shape[0]

    @property
    def ndim(self):
        return self.data.shape[1]

    @property
    def mean(self):
        if self._mean is None:
            self._mean = np.mean(self.data, axis=0)
        return self._mean

    @property
    def variance(self):
        if self._variance is None:
            self._variance = np.var(self.data, axis=0)
        return self._variance

    @property
    def effective_sample_size(self):
        if self._effective_sample_size is None and self.target is not None:
            try:
                self._effective_sample_size = effective_sample_size(
                    self, self.target.mean, self.target.variance)
            except AttributeError:
                # target may not have known mean/variance
                pass
        return self._effective_sample_size

    @property
    def bin_wise_chi2(self):
        if self._bin_wise_chi2 is None and self.target is not None:
            self._bin_wise_chi2 = bin_wise_chi2(self)
        return self._bin_wise_chi2

    def plot(self):
        if self.ndim == 1:
            return plot1d(self, target=self.target)
        if self.ndim == 2:
            return plot2d(self, target=self.target)

    def save(self, file_path=None):
        if file_path is None:
            file_path = type(self).__name__ + '-' + str(int(time.time()))
        path, name = os.path.split(file_path)

        info = {entry[0]: repr(getattr(self, entry[0]))
                for entry in self._sample_info}
        info['type'] = type(self).__name__
        info['target'] = repr(self.target)

        np.save(os.path.join(path, name + '-data.npy'), self.data)
        with open(os.path.join(path, name + '.json'), 'w') as fp:
            json.dump(info, fp, indent=2)

    def _data_table(self):
        titles = [entry[1] for entry in self._sample_info]
        entries = []
        for entry in self._sample_info:
            value = getattr(self, entry[0])
            try:
                entries.append(entry[2] % value)
            except TypeError:
                entries.append('N/A')

        return titles, entries

    def _repr_html_(self):
        titles, entries = self._data_table()
        info = ['<h3>' + type(self).__name__ + '</h3>',
                '<table><tr><th style="text-align:left;">' +
                '</th><th style="text-align:left;">'.join(titles) +
                '</th></tr><tr><td style="text-align:left;">' +
                '</td><td style="text-align:left;">'.join(entries) +
                '</td></tr></table>']
        return '\n'.join(info)

    def _repr_png_(self):
        self.plot()

    def __repr__(self):
        return (type(self).__name__ + '\n\t' + '\n\t'.join(
            '%s: %s' % (t, e) for t, e in zip(*self._data_table())))

class UniformSampler(object):
    """Uniform sampler.
    
    Produces uniformly distributed points in a [0, 1] hypercube. 
    If a target is given, the corresponding weights will be calculated.
    """
    def __init__(self, target: Optional[Density] = None) -> None:
        self.target = target

    def sample(self, sample_size: int) -> Sample:
        data=np.random.rand(sample_size, self.target.ndim)
        if self.target is not None:
            weights = self.target.pdf(data)
            return Sample(data=data, target=self.target, pdf=weights, weights=weights)
        else:
            return Sample(data=data)

class AcceptRejectSampler(object):
    """ Acceptance Rejection method for sampling a given pdf.
    
    The method uses a known distribution and sampling method to propose
    samples which are then accepted with the probability
    pdf(x)/(c * sampling_pdf(x)), thus producing the desired distribution. 
    The resulting sample is unweighted.
    
    .. todo::
        Handle points that lie above the bound.
    """

    def __init__(self, target: Density, bound: float, 
            sampler: Optional[any] = None, sampling_pdf: Optional[Callable[[any], any]] = None) -> None:
        """
        Parameters
        ----------
        target
            Unnormalized desired probability distribution of the sample.
        bound
            Constant such that pdf(x) <= bound * sampling_pdf(x)
            for all x in the range of sampling.
        sampler
            The sampler which generates the sample. The default is a uniform sampler.
        """
        self.target = target
        self.bound = bound
        self.ndim = target.ndim

        if sampler is None:
            sampler = UniformSampler(target)
            def sampling_pdf(x):
                return np.ones(x.size)

        self.sampler = sampler
        self.sampling_pdf = sampling_pdf

    def sample(self, sample_size: int) -> None:
        x = np.empty((sample_size, self.ndim))

        indices = np.arange(sample_size)
        while indices.size > 0:
            proposal = self.sampler.sample(indices.size).data
            accept = np.random.rand(indices.size) * self.bound * self.sampling_pdf(proposal) <= self.target.pdf(proposal)
            x[indices[accept]] = proposal[accept]
            indices = indices[np.logical_not(accept)]
        return Sample(data=x, target=self.target)
