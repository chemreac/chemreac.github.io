#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analytic error scaling vs. number of bins
-----------------------------------------

:download:`examples/analytic_N_scaling.py` plots the error in the solution
as function of number of bins. We expect different
behaviour depending on the number of stencil points used.
(N**-2, N**-4 and N**-6 for 3, 5 and 7 stencil points respectively)

::

 $ python analytic_N_scaling.py --help

.. exec::
   echo "::\\n\\n"
   python examples/examples/analytic_N_scaling.py --help | sed "s/^/   /"


Here is an example generated by:

::

 $ python analytic_N_scaling.py --nNs 6 --plot --savefig analytic_N_scaling.png


.. image:: ../_generated/analytic_N_scaling.png

"""

from __future__ import (
    print_function, division, absolute_import, unicode_literals
)

import argh
import numpy as np

from chemreac import FLAT, CYLINDRICAL, SPHERICAL, Geom_names
from chemreac.util.plotting import save_and_or_show_plot

from analytic_diffusion import (
    integrate_rd
)


def main(plot=False, savefig='None', nNs=7, Ns=None, rates='0,0.1',
         nfit='7,5,4'):
    import matplotlib.pyplot as plt
    nstencils = [3, 5, 7]
    nfit = [float(_) for _ in nfit.split(',')]
    c = 'rbk'
    m = 'osd'

    if Ns is None:
        Ns = [8*(2**i) for i in range(nNs)]
    else:
        Ns = list(map(int, Ns.split(',')))
        nNs = len(Ns)

    if plot:
        plt.figure(figsize=(8, 10))

    rates = list(map(float, rates.split(',')))
    for gi, geom in enumerate([FLAT, CYLINDRICAL, SPHERICAL]):
        for ri, rate in enumerate(rates):
            for si, nstencil in enumerate(nstencils):
                print(Geom_names[geom], nstencil, rate)
                tout, yout, info, rmsd_over_atol, sys = zip(*[
                    integrate_rd(N=N, nstencil=nstencil, k=rate,
                                 geom='fcs'[geom], atol=1e-8, rtol=1e-10)
                    for N in Ns])
                print('\n'.join(str(N)+': '+str(nfo) for
                                N, nfo in zip(Ns, info)))
                err = np.average(rmsd_over_atol, axis=1)
                logNs = np.log(Ns)
                logerr = np.log(err)

                if plot:
                    p = np.polyfit(logNs[:nfit[si]], logerr[:nfit[si]], 1)
                    ax = plt.subplot(3, 2, gi*2 + ri + 1)
                    ax.set_xscale('log', basex=2)
                    ax.set_yscale('log', basey=2)
                    ax.plot(Ns, err, marker=m[si], ls='None', c=c[si])
                    ax.plot(
                        Ns[:nNs-si], np.exp(np.polyval(p, logNs[:nNs-si])),
                        ls='--', c=c[si],
                        label=str(nstencil)+': '+str(round(-p[0], 1)))
                    plt.xlabel('N')
                    ax = plt.gca()
                    # ax.set_xticklabels(map(str, Ns))
                    plt.ylabel('RMSD/atol')
                    plt.legend(loc='best', prop={'size': 10})
                    if rate == 0:
                        plt.title('{} diffusion'.format(Geom_names[geom]))
                    else:
                        plt.title('{} diffusion + 1 decay'.format(
                                  Geom_names[geom]))

    if plot:
        plt.tight_layout()
        save_and_or_show_plot(savefig=savefig)


if __name__ == '__main__':
    argh.dispatch_command(main, output_file=None)
