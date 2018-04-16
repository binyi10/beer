'Test the expfamily module.'


import numpy as np
from scipy.special import gammaln, psi
import sys
import torch
import unittest

sys.path.insert(0, './')
import beer


torch.manual_seed(10)

TOLPLACES = 4
TOL = 10 ** (-TOLPLACES)


#######################################################################
# Computations using numpy for testing.
#######################################################################

def dirichlet_log_norm(natural_params):
    return -gammaln(np.sum(natural_params + 1)) \
        + np.sum(gammaln(natural_params + 1))


def dirichlet_grad_log_norm(natural_params):
    return -psi(np.sum(natural_params + 1)) + psi(natural_params + 1)


def normalgamma_log_norm(natural_params):
    np1, np2, np3, np4 = natural_params.reshape(4, -1)
    lognorm = gammaln(.5 * (np4 + 1))
    lognorm += -.5 * np.log(np3)
    lognorm += -.5 * (np4 + 1) * np.log(.5 * (np1 - ((np2**2) / np3)))
    return lognorm.sum()


def normalgamma_grad_log_norm(natural_params):
    np1, np2, np3, np4 = natural_params.reshape(4, -1)
    grad1 = -(np4 + 1) / (2 * (np1 - ((np2 ** 2) / np3)))
    grad2 = (np2 * (np4 + 1)) / (np3 * np1 - (np2 ** 2))
    grad3 = - 1 / (2 * np3) - ((np2 ** 2) * (np4 + 1)) \
        / (2 * np3 * (np3 * np1 - (np2 ** 2)))
    grad4 = .5 * psi(.5 * (np4 + 1)) \
        - .5 *np.log(.5 * (np1 - ((np2 ** 2) / np3)))
    return np.hstack([grad1, grad2, grad3, grad4])


def normalwishart_split_np(natural_params):
    D = int(.5 * (-1 + np.sqrt(1 + 4 * len(natural_params[:-2]))))
    np1, np2 = natural_params[:int(D**2)].reshape(D, D), \
         natural_params[int(D**2):-2]
    np3, np4 = natural_params[-2:]
    return np1, np2, np3, np4, D


def normalwishart_log_norm(natural_params):
    np1, np2, np3, np4, D = normalwishart_split_np(natural_params)
    lognorm = .5 * ((np4 + D) * D * np.log(2) - D * np.log(np3))
    sign, logdet = np.linalg.slogdet(np1 - np.outer(np2, np2) / np3)
    lognorm += -.5 * (np4 + D) * sign * logdet
    lognorm += np.sum(gammaln(.5 * (np4 + D + 1 - np.arange(1, D + 1, 1))))
    return lognorm


def normalwishart_grad_log_norm(natural_params):
    np1, np2, np3, np4, D = normalwishart_split_np(natural_params)
    outer = np.outer(np2, np2) / np3
    matrix = (np1 - outer)
    sign, logdet = np.linalg.slogdet(matrix)
    inv_matrix = np.linalg.inv(matrix)

    grad1 = -.5 * (np4 + D) * inv_matrix
    grad2 = (np4 + D) * inv_matrix @ (np2 / np3)
    grad3 = - D / (2 * np3) - .5 * (np4 + D) \
        * np.trace(inv_matrix @ (outer / np3))
    grad4 = .5 * np.sum(psi(.5 * (np4 + D + 1 - np.arange(1, D + 1, 1))))
    grad4 += -.5 * sign * logdet + .5 * D * np.log(2)
    return np.hstack([grad1.reshape(-1), grad2, grad3, grad4])


def jointnormalwishart_split_np(natural_params, ncomp=1):
    D = int(.5 * (-ncomp + np.sqrt(ncomp**2 + 4 * len(natural_params[:-(ncomp + 1)]))))
    np1, np2s = natural_params[:int(D**2)].reshape(D, D), \
         natural_params[int(D**2):-(ncomp+1)].reshape(ncomp, D)
    np3s = natural_params[-(ncomp+1): -1]
    np4 = natural_params[-1]
    return np1, np2s, np3s, np4, D


def jointnormalwishart_log_norm(natural_params, ncomp):
    np1, np2s, np3s, np4, D = jointnormalwishart_split_np(natural_params, ncomp)
    lognorm = .5 * ((np4 + D) * D * np.log(2) - D * np.log(np3s).sum())
    quad_exp = ((np2s[:, None, :] * np2s[:, :, None]) / np3s[:, None, None]).sum(axis=0)
    sign, logdet = np.linalg.slogdet(np1 - quad_exp)
    lognorm += -.5 * (np4 + D) * sign * logdet
    lognorm += np.sum(gammaln(.5 * (np4 + D + 1 - np.arange(1, D + 1, 1))))
    return lognorm


def normal_fc_split_np(natural_params):
    D = int(.5 * (-1 + np.sqrt(1 + 4 * len(natural_params))))
    np1, np2 = natural_params[:int(D**2)].reshape(D, D), \
         natural_params[int(D**2):]
    return np1, np2, D


def normal_fc_log_norm(natural_params):
    np1, np2, D = normal_fc_split_np(natural_params)
    inv_np1 = np.linalg.inv(np1)
    sign, logdet = np.linalg.slogdet(-2 * np1)
    lognorm = -.5 * sign * logdet - .25 * (np2[None, :] @ inv_np1) @ np2
    return lognorm


def normal_fc_grad_log_norm(natural_params):
    np1, np2, D = normal_fc_split_np(natural_params)
    cov = np.linalg.inv(-2 * np1)
    mean = cov @ np2
    return np.hstack([(cov + np.outer(mean, mean)).reshape(-1), mean])


#######################################################################
# Abstract base class for implementing the logic of the tests.
#######################################################################


class TestDirichletPrior:

    def test_create(self):
        model = beer.DirichletPrior(self.prior_counts)
        self.assertTrue(isinstance(model, beer.ExpFamilyPrior))
        self.assertTrue(np.allclose(model.natural_params.numpy(),
            self.prior_counts.numpy() - 1, rtol=TOL, atol=TOL))

    def test_exp_sufficient_statistics(self):
        model = beer.DirichletPrior(self.prior_counts)
        model_s_stats = model.expected_sufficient_statistics.numpy()
        natural_params = model.natural_params.numpy()
        s_stats = dirichlet_grad_log_norm(natural_params)
        self.assertTrue(np.allclose(model_s_stats, s_stats, rtol=TOL, atol=TOL))

    def test_kl_divergence(self):
        model1 = beer.DirichletPrior(self.prior_counts)
        model2 = beer.DirichletPrior(self.prior_counts)
        div = beer.kl_div(model1, model2)
        self.assertAlmostEqual(div, 0., places=TOLPLACES)

    def test_log_norm(self):
        model = beer.DirichletPrior(self.prior_counts)
        model_log_norm = model.log_norm.numpy()
        natural_params = model.natural_params.numpy()
        log_norm = dirichlet_log_norm(natural_params)
        self.assertAlmostEqual(model_log_norm, log_norm, places=TOLPLACES)


class TestNormalGammaPrior:

    def test_create(self):
        model = beer.NormalGammaPrior(self.mean, self.precision,
                                      self.prior_count)
        self.assertTrue(isinstance(model, beer.ExpFamilyPrior))

    def test_exp_sufficient_statistics(self):
        model = beer.NormalGammaPrior(self.mean, self.precision,
                                      self.prior_count)
        model_s_stats = model.expected_sufficient_statistics.numpy()
        natural_params = model.natural_params.numpy()
        s_stats = normalgamma_grad_log_norm(natural_params)
        self.assertTrue(np.allclose(model_s_stats, s_stats, rtol=TOL, atol=TOL))

    def test_kl_divergence(self):
        model1 = beer.NormalGammaPrior(self.mean, self.precision,
                                       self.prior_count)
        model2 = beer.NormalGammaPrior(self.mean, self.precision,
                                       self.prior_count)
        div = beer.kl_div(model1, model2)
        self.assertAlmostEqual(div, 0., places=TOLPLACES)

    def test_log_norm(self):
        model = beer.NormalGammaPrior(self.mean, self.precision,
                                      self.prior_count)
        model_log_norm = model.log_norm.numpy()
        natural_params = model.natural_params.numpy()
        log_norm = normalgamma_log_norm(natural_params)
        self.assertAlmostEqual(model_log_norm, log_norm, places=TOLPLACES)


class TestNormalWishartPrior:

    def test_create(self):
        model = beer.NormalWishartPrior(self.mean, self.cov, self.prior_count)
        self.assertTrue(isinstance(model, beer.ExpFamilyPrior))

    def test_exp_sufficient_statistics(self):
        model = beer.NormalWishartPrior(self.mean, self.cov, self.prior_count)
        model_s_stats = model.expected_sufficient_statistics.numpy()
        natural_params = model.natural_params.numpy()
        s_stats = normalwishart_grad_log_norm(natural_params)
        self.assertTrue(np.allclose(model_s_stats, s_stats, rtol=TOL, atol=TOL))

    def test_kl_divergence(self):
        model1 = beer.NormalWishartPrior(self.mean, self.cov, self.prior_count)
        model2 = beer.NormalWishartPrior(self.mean, self.cov, self.prior_count)
        div = beer.kl_div(model1, model2)
        self.assertAlmostEqual(div, 0., places=TOLPLACES)

    def test_log_norm(self):
        model = beer.NormalWishartPrior(self.mean, self.cov, self.prior_count)
        model_log_norm = model.log_norm.numpy()
        natural_params = model.natural_params.numpy()
        log_norm = normalwishart_log_norm(natural_params)
        self.assertAlmostEqual(model_log_norm, log_norm, places=TOLPLACES)


class TestJointNormalWishartPrior:

    def test_create(self):
        model = beer.JointNormalWishartPrior(self.means, self.cov, self.prior_count)
        self.assertTrue(isinstance(model, beer.ExpFamilyPrior))

    def test_kl_divergence(self):
        model1 = beer.JointNormalWishartPrior(self.means, self.cov, self.prior_count)
        model2 = beer.JointNormalWishartPrior(self.means, self.cov, self.prior_count)
        div = beer.kl_div(model1, model2)
        self.assertAlmostEqual(div, 0., places=TOLPLACES)

    def test_log_norm(self):
        model = beer.JointNormalWishartPrior(self.means, self.cov, self.prior_count)
        model_log_norm = model.log_norm.numpy()
        natural_params = model.natural_params.numpy()
        log_norm = jointnormalwishart_log_norm(natural_params, ncomp=self.ncomp)
        self.assertAlmostEqual(model_log_norm, log_norm, places=TOLPLACES)

    # We don't test the automatic differentiation of the
    # log-normalizer. As long as the log-normlizer is correct, then
    # pytorch should gives us the right gradient.
    #def test_exp_sufficient_statistics(self):
    #   pass


class TestNormalPrior:

    def test_create(self):
        model = beer.NormalPrior(self.mean, self.cov)
        self.assertTrue(isinstance(model, beer.ExpFamilyPrior))

    def test_exp_sufficient_statistics(self):
        model = beer.NormalPrior(self.mean, self.cov)
        model_s_stats = model.expected_sufficient_statistics.numpy()
        natural_params = model.natural_params.numpy()
        s_stats = normal_fc_grad_log_norm(natural_params)
        self.assertTrue(np.allclose(model_s_stats, s_stats, rtol=TOL, atol=TOL))

    def test_kl_divergence(self):
        model1 = beer.NormalPrior(self.mean, self.cov)
        model2 = beer.NormalPrior(self.mean, self.cov)
        div = beer.kl_div(model1, model2)
        self.assertAlmostEqual(div, 0., places=TOLPLACES)

    def test_log_norm(self):
        model = beer.NormalPrior(self.mean, self.cov)
        model_log_norm = model.log_norm.numpy()
        natural_params = model.natural_params.numpy()
        log_norm = normal_fc_log_norm(natural_params)[0]
        self.assertAlmostEqual(model_log_norm, log_norm, places=TOLPLACES)


#######################################################################
# Testing condition.
#######################################################################


tests = [
    (TestDirichletPrior, {'prior_counts': torch.ones(1).float()}),
    (TestDirichletPrior, {'prior_counts': torch.ones(1).double()}),
    (TestDirichletPrior, {'prior_counts': torch.ones(2).float()}),
    (TestDirichletPrior, {'prior_counts': torch.ones(2).float()}),
    (TestDirichletPrior, {'prior_counts': torch.ones(10).double()}),
    (TestDirichletPrior, {'prior_counts': torch.ones(10).double()}),
    (TestDirichletPrior, {'prior_counts': torch.FloatTensor([1, 2, 3, 4, 5])}),
    (TestDirichletPrior, {'prior_counts': torch.DoubleTensor([1, 2, 3, 4, 5])}),

    (TestNormalGammaPrior, {'mean': torch.zeros(2).float(),
        'precision': torch.ones(2).float(), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.zeros(2).double(),
        'precision': torch.ones(2).double(), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).float(),
        'precision': torch.ones(2).float(), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).double(),
        'precision': torch.ones(2).double(), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).float(),
        'precision': torch.FloatTensor([1e-4, 2e-4]), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).double(),
        'precision': torch.DoubleTensor([1e-4, 2e-4]), 'prior_count': 1.}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).float(),
        'precision': torch.FloatTensor([1e-4, 2e-4]), 'prior_count': 1e-3}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).double(),
        'precision': torch.DoubleTensor([1e-4, 2e-4]), 'prior_count': 1e-8}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).float(),
        'precision': torch.FloatTensor([1e-4, 2e-4]), 'prior_count': 1e4}),
    (TestNormalGammaPrior, {'mean': torch.randn(2).double(),
        'precision': torch.DoubleTensor([1e-4, 2e-4]), 'prior_count': 1e8}),

    (TestNormalWishartPrior, {'mean': torch.zeros(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.zeros(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1.}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1e-3}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1e-8}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1e2}),
    (TestNormalWishartPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1e8}),

    (TestJointNormalWishartPrior, {'means': torch.zeros(3, 2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.zeros(3, 2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1., 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1e-3, 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1e-8, 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).float(),
        'cov': torch.eye(2).float() * 1e-4, 'prior_count': 1e2, 'ncomp': 3}),
    (TestJointNormalWishartPrior, {'means': torch.randn(3, 2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1e8, 'ncomp': 3}),

    (TestNormalPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float()}),
    (TestNormalPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double()}),
    (TestNormalPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float()}),
    (TestNormalPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double()}),
    (TestNormalPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4}),
    (TestNormalPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8}),
    (TestNormalPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4}),
    (TestNormalPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8}),
    (TestNormalPrior, {'mean': torch.randn(2).float(),
        'cov': torch.eye(2).float() * 1e-4}),
    (TestNormalPrior, {'mean': torch.randn(2).double(),
        'cov': torch.eye(2).double() * 1e-8}),
]


module = sys.modules[__name__]
for i, test in enumerate(tests, start=1):
    name = test[0].__name__ + 'Test' + str(i)
    setattr(module, name, type(name, (unittest.TestCase, test[0]),  test[1]))


if __name__ == '__main__':
    unittest.main()

