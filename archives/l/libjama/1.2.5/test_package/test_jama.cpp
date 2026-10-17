// Consumer test for the installed libjama package.
//
// Exercises the numeric results of every decomposition JAMA/C++ implements,
// using only the public headers (the storage types come from the libtnt
// dependency, which the package propagates).
#include <cmath>
#include <cstdio>

#include <jama/jama_cholesky.h>
#include <jama/jama_eig.h>
#include <jama/jama_lu.h>
#include <jama/jama_qr.h>
#include <jama/jama_svd.h>

static int checks;
static int failures;

static void check(bool ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

static bool near(double a, double b, double eps = 1e-9)
{
    return std::fabs(a - b) <= eps;
}

int main(void)
{
    // LU: solve [[4,3],[6,3]] x = [10,12] -> x = [1,2]
    TNT::Array2D<double> a(2, 2);
    a[0][0] = 4.0; a[0][1] = 3.0;
    a[1][0] = 6.0; a[1][1] = 3.0;
    JAMA::LU<double> lu(a);
    TNT::Array1D<double> b(2);
    b[0] = 10.0; b[1] = 12.0;
    TNT::Array1D<double> x = lu.solve(b);
    check(x.dim() == 2 && near(x[0], 1.0) && near(x[1], 2.0),
          "LU.solve([[4,3],[6,3]],[10,12]) == [1,2]");
    check(lu.isNonsingular(), "LU.isNonsingular()");
    check(near(lu.det(), -6.0), "LU.det([[4,3],[6,3]]) == -6");

    // QR least squares: A = [1,1; 1,2; 1,3], b = [1,2,2]
    // normal equations -> x = [2/3, 1/2]
    TNT::Array2D<double> qa(3, 2);
    qa[0][0] = 1.0; qa[0][1] = 1.0;
    qa[1][0] = 1.0; qa[1][1] = 2.0;
    qa[2][0] = 1.0; qa[2][1] = 3.0;
    JAMA::QR<double> qr(qa);
    TNT::Array1D<double> qb(3);
    qb[0] = 1.0; qb[1] = 2.0; qb[2] = 2.0;
    TNT::Array1D<double> qx = qr.solve(qb);
    check(qx.dim() == 2 && near(qx[0], 2.0 / 3.0) && near(qx[1], 0.5),
          "QR.solve least squares == [2/3, 1/2]");
    check(qr.isFullRank(), "QR.isFullRank()");

    // Cholesky on the SPD matrix [[4,2],[2,3]], solve [6,5] -> [1,1]
    TNT::Array2D<double> c(2, 2);
    c[0][0] = 4.0; c[0][1] = 2.0;
    c[1][0] = 2.0; c[1][1] = 3.0;
    JAMA::Cholesky<double> chol(c);
    TNT::Array1D<double> cb(2);
    cb[0] = 6.0; cb[1] = 5.0;
    TNT::Array1D<double> cx = chol.solve(cb);
    check(chol.is_spd(), "Cholesky.is_spd()");
    check(cx.dim() == 2 && near(cx[0], 1.0) && near(cx[1], 1.0),
          "Cholesky.solve([[4,2],[2,3]],[6,5]) == [1,1]");
    TNT::Array2D<double> l = chol.getL();
    check(near(l[0][0], 2.0) && near(l[1][0], 1.0)
              && near(l[1][1], std::sqrt(2.0)),
          "Cholesky.getL() == [[2,0],[1,sqrt(2)]]");

    // SVD of the diagonal matrix diag(3,2)
    TNT::Array2D<double> s(2, 2);
    s[0][0] = 3.0; s[0][1] = 0.0;
    s[1][0] = 0.0; s[1][1] = 2.0;
    JAMA::SVD<double> svd(s);
    TNT::Array1D<double> sv(2);
    svd.getSingularValues(sv);
    check(sv.dim() == 2 && near(sv[0], 3.0) && near(sv[1], 2.0),
          "SVD singular values of diag(3,2) == [3,2]");
    check(near(svd.norm2(), 3.0), "SVD.norm2() == 3");
    check(svd.rank() == 2, "SVD.rank() == 2");

    // Eigenvalues of the symmetric matrix [[2,1],[1,2]] -> {1,3}
    TNT::Array2D<double> e(2, 2);
    e[0][0] = 2.0; e[0][1] = 1.0;
    e[1][0] = 1.0; e[1][1] = 2.0;
    JAMA::Eigenvalue<double> eig(e);
    TNT::Array1D<double> d(2);
    TNT::Array1D<double> ie(2);
    eig.getRealEigenvalues(d);
    eig.getImagEigenvalues(ie);
    double lo = d[0] < d[1] ? d[0] : d[1];
    double hi = d[0] < d[1] ? d[1] : d[0];
    check(near(lo, 1.0) && near(hi, 3.0),
          "Eigenvalue real values of [[2,1],[1,2]] == {1,3}");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
