#include <math.h>
#include <stdio.h>

extern double ddot_(const int *, const double *, const int *,
                    const double *, const int *);
extern void dgemm_(const char *, const char *, const int *, const int *,
                   const int *, const double *, const double *, const int *,
                   const double *, const int *, const double *, double *,
                   const int *);
extern void dgemv_(const char *, const int *, const int *, const double *,
                   const double *, const int *, const double *, const int *,
                   const double *, double *, const int *);
extern double dnrm2_(const int *, const double *, const int *);
extern void dscal_(const int *, const double *, double *, const int *);
extern int lsame_(const char *, const char *);

static int failures;
static int total;

static void check(int ok, const char *name)
{
    total++;
    printf("[%s] %s\n", ok ? "PASS" : "FAIL", name);
    if (!ok) {
        failures++;
    }
}

static int close_to(double actual, double expected)
{
    return fabs(actual - expected) < 1e-10;
}

int main(void)
{
    const int one = 1;
    const int two = 2;
    const int three = 3;
    const int four = 4;
    const double alpha = 1.0;
    const double beta = 0.0;
    const double scale = 2.0;
    const char no_transpose = 'N';
    double x[] = {1.0, 2.0, 3.0, 4.0};
    double y[] = {5.0, 6.0, 7.0, 8.0};
    double matrix_a[] = {1.0, 2.0, 3.0, 4.0};
    double matrix_b[] = {5.0, 6.0, 7.0, 8.0};
    double matrix_c[] = {0.0, 0.0, 0.0, 0.0};
    double vector_y[] = {0.0, 0.0};
    double scaled[] = {1.0, 2.0, 3.0};

    check(close_to(ddot_(&four, x, &one, y, &one), 70.0), "ddot");

    dgemm_(&no_transpose, &no_transpose, &two, &two, &two, &alpha,
           matrix_a, &two, matrix_b, &two, &beta, matrix_c, &two);
    check(close_to(matrix_c[0], 23.0) && close_to(matrix_c[1], 34.0) &&
              close_to(matrix_c[2], 31.0) && close_to(matrix_c[3], 46.0),
          "dgemm");

    dgemv_(&no_transpose, &two, &two, &alpha, matrix_a, &two, x, &one,
           &beta, vector_y, &one);
    check(close_to(vector_y[0], 7.0) && close_to(vector_y[1], 10.0), "dgemv");

    check(close_to(dnrm2_(&four, x, &one), sqrt(30.0)), "dnrm2");

    dscal_(&three, &scale, scaled, &one);
    check(close_to(scaled[0], 2.0) && close_to(scaled[1], 4.0) &&
              close_to(scaled[2], 6.0),
          "dscal");

    check(lsame_("n", "N") != 0, "lsame");

    printf("BLAS consumer assertions: %d total, %d failed\n", total, failures);
    return failures == 0 ? 0 : 1;
}
