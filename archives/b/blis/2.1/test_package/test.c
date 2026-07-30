#include <cblas.h>
#include <math.h>
#include <stdio.h>

int main(void)
{
    const double a[] = {1.0, 2.0, 3.0, 4.0};
    const double b[] = {5.0, 6.0, 7.0, 8.0};
    double c[4] = {0.0, 0.0, 0.0, 0.0};

    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                2, 2, 2, 1.0, a, 2, b, 2, 0.0, c, 2);

    if (fabs(c[0] - 19.0) > 1e-12 || fabs(c[1] - 22.0) > 1e-12 ||
        fabs(c[2] - 43.0) > 1e-12 || fabs(c[3] - 50.0) > 1e-12) {
        fprintf(stderr, "cblas_dgemm returned unexpected values\n");
        return 1;
    }

    puts("blis CBLAS dgemm test passed");
    return 0;
}
