/* kernsmooth.h — C interface to the KernSmooth 2.23-26 Fortran 77 core.
 *
 * KernSmooth (M. P. Wand & B. D. Ripley; functions for kernel smoothing
 * supporting Wand & Jones (1995) "Kernel Smoothing") ships its numerical
 * core as Fortran 77 subroutines (src/*.f). Upstream builds them only as
 * part of the R package (via src/init.c, which requires R headers), so
 * this header is provided by the HarmonyOS port to make the same routines
 * callable from plain C / C++ consumers as a standalone static library.
 *
 * F77 name mangling on OHOS/clang+flang: lowercase symbol + trailing
 * underscore  (subroutine locpol -> symbol locpol_).
 *
 * ALL ARGUMENTS ARE PASSED BY REFERENCE (Fortran calling convention).
 * Arrays are column-major, matching Fortran layout.
 *
 * NOTE on lbtwod: the Fortran source file is named linbin2D.f but the
 * subroutines it defines are named lbtwod and 2Dlinbin; upstream init.c
 * registers the symbol as "lbtwod".
 */
#ifndef KERNSMOOTH_H
#define KERNSMOOTH_H

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* blkest.f — blocked polynomial estimates (direct plug-in bandwidth)  */
/* ------------------------------------------------------------------ */
/* X, Y      : sorted (x,y) data, length n
 * n         : number of observations
 * q         : degree of the polynomial fit
 * qq        : q+1, number of columns of the design matrix
 * Nval      : number of blocks in the partition
 * Xj, Yj    : workspace, length n
 * coef      : workspace, length qq
 * Xmat      : workspace, dimension n x qq
 * wk        : workspace, length n
 * qraux     : workspace, length qq
 * sigsqe    : OUT residual variance  = RSS / (n - qq*Nval)
 * th22e     : OUT mean squared 2nd-derivative estimate
 * th24e     : OUT estimate of the 2nd/4th derivative functional
 */
void blkest_(double *X, double *Y, int *n, int *q, int *qq, int *Nval,
             double *Xj, double *Yj, double *coef, double *Xmat,
             double *wk, double *qraux, double *sigsqe,
             double *th22e, double *th24e);

/* ------------------------------------------------------------------ */
/* cp.f — Mallows' Cp values for blocked polynomial fits               */
/* ------------------------------------------------------------------ */
/* X, Y : sorted data, length n            n    : number of observations
 * qq   : q+1 design columns               Nmax : max number of blocks
 * RSS  : IN/OUT residual sums of squares, length Nmax
 * Xj, Yj, wk : workspace, length n        coef : workspace, length qq
 * Xmat : workspace, n x qq                qraux: workspace, length qq
 * Cpvals : OUT Mallows' Cp values, length Nmax
 */
void cp_(double *X, double *Y, int *n, int *qq, int *Nmax, double *RSS,
         double *Xj, double *Yj, double *coef, double *Xmat, double *wk,
         double *qraux, double *Cpvals);

/* ------------------------------------------------------------------ */
/* linbin.f — univariate linear binning                                */
/* ------------------------------------------------------------------ */
/* X : data (length n);  a, b : grid range;  M : number of grid points
 * trun : 0 = give end-observation weight to end grid points, 1 = truncate
 * gcnts : OUT bin counts, length M
 */
void linbin_(double *X, int *n, double *a, double *b,
             int *M, int *trun, double *gcnts);

/* ------------------------------------------------------------------ */
/* linbin2D.f — bivariate linear binning (symbols: lbtwod)             */
/* ------------------------------------------------------------------ */
/* X : interleaved (x1,y1,x2,y2,...) pairs, length 2*n
 * a1,a2,b1,b2 : grid ranges;  M1,M2 : grid sizes
 * gcnts : OUT M1*M2 bin counts (column-major)
 */
void lbtwod_(double *X, int *n, double *a1, double *a2,
             double *b1, double *b2, int *m1, int *m2, double *gcounts);

/* ------------------------------------------------------------------ */
/* locpoly.f — binned local polynomial kernel regression (symbol locpol)*/
/* ------------------------------------------------------------------ */
/* xcnts, ycnts : binned data, length M
 * idrv   : derivative order to estimate (0 = regression function)
 * delta  : bin width  = (b-a)/(M-1)
 * hdisc  : discretised bandwidth(s), length iQ
 * Lvec   : kernel support half-widths, length iQ
 * indic  : index of the bandwidth used at each grid point, length M
 * midpts : OUT kernel midpoints, length iQ
 * M      : number of grid points
 * iQ     : number of discretised bandwidths
 * fkap   : workspace, length 2*sum(Lvec) + iQ
 * ipp    : pp  = degree+1  (rows/cols of Smat)
 * ippp   : ppp = 2*degree+1 (columns of ss)
 * ss, tt : workspace, dimensions M x ippp and M x ipp
 * Smat   : workspace, ipp x ipp      Tvec : workspace, length ipp
 * ipvt   : workspace, length ipp
 * cvest  : OUT the estimated curve, length M
 */
void locpol_(double *xcounts, double *ycounts, int *idrv, double *delta,
             double *hdisc, int *lvec, int *indic, int *midpts,
             int *m, int *iq, double *fkap, int *ipp, int *ippp,
             double *ss, double *tt, double *smat, double *tvec,
             int *ipvt, double *curvest);

/* ------------------------------------------------------------------ */
/* rlbin.f — linear binning of regression data                         */
/* ------------------------------------------------------------------ */
/* X, Y : data, length n;  a, b : range;  M : grid size
 * trun  : 0 = end-weight, 1 = truncate
 * xcnts, ycnts : OUT binned counts, length M
 */
void rlbin_(double *X, double *Y, int *n, double *a, double *b,
            int *M, int *trun, double *xcounts, double *ycounts);

/* ------------------------------------------------------------------ */
/* sdiag.f — binned diagonal entries of the smoother matrix             */
/* ------------------------------------------------------------------ */
/* xcnts : binned counts, length M       delta : bin width
 * hdisc : bandwidth(s), length iQ       lvec  : support widths, length iQ
 * indic : bandwidth index per point     midpts: OUT, length iQ
 * M, iQ : grid size / #bandwidths       fkap  : workspace
 * ipp   : pp = degree+1                 ippp  : ppp = 2*degree+1
 * ss    : workspace M x ippp            smat  : workspace ipp x ipp
 * work  : workspace                     et    : workspace
 * ipvt  : workspace, length ipp         sd    : OUT diagonal entries, length M
 */
void sdiag_(double *xcounts, double *delta, double *hdisc, int *lvec,
            int *indic, int *midpts, int *m, int *iq, double *fkap,
            int *ipp, int *ippp, double *ss, double *smat, double *work,
            double *et, int *ipvt, double *sd);

/* ------------------------------------------------------------------ */
/* sstdiag.f — standard-error diagonal entries (symbol sstdg)          */
/* ------------------------------------------------------------------ */
/* Arguments mirror sdiag_, with uu/umat extra workspaces and
 * det : workspace for the determinant, sstd : OUT entries, length M.
 */
void sstdg_(double *xcounts, double *delta, double *hdisc, int *lvec,
            int *indic, int *midpts, int *m, int *iq, double *fkap,
            int *ipp, int *ippp, double *ss, double *uu, double *smat,
            double *umat, double *work, double *det, int *ipvt,
            double *sstd);

/* ------------------------------------------------------------------ */
/* Bundled LINPACK helpers (public-domain netlib LINPACK) —            */
/* required by blkest_/cp_.  Exported for completeness; consumers       */
/* normally do not call these directly.                                */
/* ------------------------------------------------------------------ */
void dqrdc_(double *x, int *ldx, int *n, int *p, double *qraux,
            int *jpvt, double *work, int *job);
void dqrsl_(double *x, int *ldx, int *n, int *k, double *qraux,
            double *y, double *qy, double *qty, double *b, double *rsd,
            double *xb, int *job, int *info);

#ifdef __cplusplus
}
#endif

#endif /* KERNSMOOTH_H */
