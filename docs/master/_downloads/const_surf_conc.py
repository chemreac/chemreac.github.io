#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diffusion from constant concentration surface
---------------------------------------------

:download:`examples/const_surf_conc.py` models a diffusion process
and reports the error from the model integration by comparison to the
analytic solution (intial concentrations are taken from Green's
function expressions for respective geometry).

::

 $ python const_surf_conc.py --help

.. exec::
   echo "::\\n\\n"
   python examples/examples/const_surf_conc.py --help | sed "s/^/   /"

Here is an example generated by:

::

 $ python const_surf_conc.py --plot --savefig const_surf_conc.png

.. image:: ../_generated/const_surf_conc.png

Solving the transformed system (:math:`\\frac{d}{dt} \\ln(c(\\ln(x), t))`):

::

 $ python const_surf_conc.py --plot --N 1024 --verbose --nstencil 3\
 --scaling 1e-20 --logx --logy --factor 1e12 --x0 1e-6\
 --atol 1e-8 --rtol 1e-8 --savefig const_surf_conc_logy_logx.png

.. image:: ../_generated/const_surf_conc_logy_logx.png


"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import *

from collections import defaultdict
from math import log

import argh
import numpy as np

from chemreac import ReactionDiffusion
from chemreac.integrate import run
from chemreac.util.grid import generate_grid
from chemreac.util.plotting import save_and_or_show_plot
from chemreac.util.testing import spat_ave_rmsd_vs_time


def analytic(x, t, D, x0, xend, logx=False, c_s=1):
    r"""
    Evaluates the analytic expression for the concentration
    in a medium with a constant source term at x=0:

    .. math ::

        c(x, t) = c_s \mathrm{erfc}\left( \frac{x}{2\sqrt{Dt}}\right)

    where :math:`c_s` is the constant surface concentration.
    """
    import scipy.special
    if t.ndim == 1:
        t = t.reshape((t.size, 1))
    x = np.exp(x) if logx else x
    return c_s * scipy.special.erfc(x/(2*(D*t)**0.5))


def integrate_rd(D=2e-3, t0=1., tend=13., x0=1e-10, xend=1.0, N=64,
                 nt=42, logt=False, logy=False, logx=False,
                 random=False, k=1.0, nstencil=3, linterpol=False,
                 rinterpol=False, num_jacobian=False, method='bdf',
                 plot=False, atol=1e-6, rtol=1e-6, factor=1e5,
                 random_seed=42, savefig='None', verbose=False,
                 scaling=1.0):
    """
    Solves the time evolution of diffusion from a constant source term.
    Optionally plots the results. In the plots time is represented by
    color scaling from black (:math:`t_0`) to red (:math:`t_{end}`)
    """
    if t0 == 0.0:
        raise ValueError("t0==0 => Dirac delta function C0 profile.")
    if random_seed:
        np.random.seed(random_seed)
    tout = np.linspace(t0, tend, nt)

    units = defaultdict(lambda: 1)
    units['amount'] = 1.0/scaling

    # Setup the grid
    x = generate_grid(x0, xend, N, logx, random=random)
    modulation = [1 if (i == 0) else 0 for i in range(N)]

    rd = ReactionDiffusion(
        2,
        [[0], [1]],
        [[1], [0]],
        [k, factor*k],
        N,
        D=[0, D],
        x=x,
        logy=logy,
        logt=logt,
        logx=logx,
        nstencil=nstencil,
        lrefl=not linterpol,
        rrefl=not rinterpol,
        modulated_rxns=[0, 1],
        modulation=[modulation, modulation],
        units=units,
        faraday=1,
        vacuum_permittivity=1
    )

    # Calc initial conditions / analytic reference values
    Cref = analytic(rd.xcenters, tout, D, x0, xend, logx).reshape(
        nt, N, 1)
    source = np.zeros_like(Cref[0, ...])
    source[0, :] = factor
    y0 = np.concatenate((source, Cref[0, ...]), axis=1)

    # Run the integration
    integr = run(rd, y0, tout, atol=atol, rtol=rtol,
                 with_jacobian=(not num_jacobian), method=method)
    Cout, info = integr.Cout, integr.info
    print("integr.Cout[0, :, 1] = ", integr.Cout[0, :, 1])
    print("integr.yout[0, :, 1] = ", integr.yout[0, :, 1])
    spat_ave_rmsd_over_atol = spat_ave_rmsd_vs_time(
        Cout[:, :, 1], Cref[:, :, 0]) / atol
    tot_ave_rmsd_over_atol = np.average(spat_ave_rmsd_over_atol)
    if plot:
        # Plot results
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6, 10))

        def _plot(y, c, ttl=None, apply_exp_on_y=False, vlines=False,
                  smooth=True):
            if vlines:
                plt.vlines(rd.x, 0, np.ones_like(rd.x)*max(y),
                           linewidth=1, colors='gray')
            if smooth:
                plt.plot(rd.xcenters, np.exp(y) if apply_exp_on_y else y,
                         c=c)
            else:
                for i, _y in enumerate(np.exp(y) if apply_exp_on_y else y):
                    plt.plot([rd.x[i], rd.x[i+1]], [_y, _y], c=c)

            plt.xlabel('x / m')
            plt.ylabel('C / M')
            if ttl:
                plt.title(ttl)

        for i in range(nt):
            kwargs = dict(smooth=(N >= 20),
                          vlines=(i == 0 and N < 20))

            c = 1-tout[i]/tend
            c = (1.0-c, .5-c/2, .5-c/2)
            plt.subplot(5, 1, 1)
            _plot(Cout[i, :, 1], c, 'Simulation (N={})'.format(rd.N),
                  **kwargs)

            plt.subplot(5, 1, 2)
            _plot(Cref[i, :, 0], c, 'Analytic', **kwargs)

            plt.subplot(5, 1, 3)
            _plot((Cout[i, :, 1]-Cref[i, :, 0])/atol, c,
                  "Abs. err. / abs. tol. (atol={0:<.3g})".format(atol),
                  **kwargs)

            plt.subplot(5, 1, 4)
            ttl = "Abs. err. / (abs. tol. + rtol*|Cref|)"
            _plot((Cout[i, :, 1]-Cref[i, :, 0])/(atol + np.abs(
                rtol*Cref[i, :, 0])), c, ttl, **kwargs)

            plt.subplot(5, 1, 5)
            plt.plot(integr.tout, spat_ave_rmsd_over_atol)
            plt.plot([integr.tout[0], integr.tout[-1]],
                     [tot_ave_rmsd_over_atol]*2, '--')
            plt.title("RMSD / atol")

        plt.tight_layout()
        save_and_or_show_plot(savefig=savefig)

    if verbose:
        print(info)

    return tout, Cout, info, rd, tot_ave_rmsd_over_atol


if __name__ == '__main__':
    argh.dispatch_command(integrate_rd, output_file=None)