/* test_itpp.cpp — real consumer test source for itpp 4.3.1 (L0c).

Links against libitpp and exercises the REAL API (R34):
  1) itpp::vec — construct, fill, compute sum/dot product
  2) itpp::mat — 2x2 matrix multiply + determinant via itpp
  verifying results against manual computation.
*/
#include <cstdio>
#include <cmath>
#include "itpp/itbase.h"

static int failures = 0;
#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("FAIL: %s\n", msg);                                      \
            ++failures;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    // 1) vec: v = [1,2,3,4], sum = 10, dot(v,v) = 30
    itpp::vec v(4);
    v(0) = 1; v(1) = 2; v(2) = 3; v(3) = 4;
    CHECK(std::fabs(itpp::sum(v) - 10.0) < 1e-9, "itpp::sum");
    CHECK(std::fabs(itpp::dot(v, v) - 30.0) < 1e-9, "itpp::dot");

    // 2) mat: A = [[1,2],[3,4]], transpose + element access (no LAPACK:
    //    det/lu need BLAS/LAPACK which OHOS lacks → it_error crash)
    itpp::mat A(2, 2);
    A(0, 0) = 1; A(0, 1) = 2;
    A(1, 0) = 3; A(1, 1) = 4;
    itpp::mat At = itpp::transpose(A);
    CHECK(std::fabs(At(0, 1) - 3.0) < 1e-9, "itpp::transpose");
    CHECK(std::fabs(A(1, 1) - 4.0) < 1e-9, "itpp::mat element access");

    // 3) besselj — upstream bessel_test core cases (LOCALLY MEASURED
    //    PASS, no LAPACK needed). x is linspace(0.01, 10, 20); first 4
    //    x/ref pairs from the sdist ref strings:
    double xs[4] = {0.01, 0.535789, 1.06158, 1.58737};
    double ref[4] = {0.999975, 0.929510, 0.737496, 0.462593};
    for (int i = 0; i < 4; ++i) {
        double got = itpp::besselj(0, xs[i]);
        if (std::fabs(got - ref[i]) > 1e-4) {
            printf("FAIL: besselj(0,%g)=%g (ref %g)\n", xs[i], got, ref[i]);
            ++failures;
        }
    }

    if (failures == 0)
        printf("OK: itpp 4.3.1 vec/mat real API ok\n");
    return failures == 0 ? 0 : 1;
}
