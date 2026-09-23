#include <cubature.h>

#include <math.h>
#include <stddef.h>
#include <stdio.h>

static int product(unsigned ndim, const double *x, void *data, unsigned fdim,
                   double *fval) {
  (void)data;
  if (ndim != 2 || fdim != 1) {
    return 1;
  }
  fval[0] = x[0] * x[1];
  return 0;
}

static int product_vectorized(unsigned ndim, size_t npt, const double *x,
                              void *data, unsigned fdim, double *fval) {
  size_t point;

  (void)data;
  if (ndim != 2 || fdim != 1) {
    return 1;
  }
  for (point = 0; point < npt; ++point) {
    fval[point] = x[point * ndim] * x[point * ndim + 1];
  }
  return 0;
}

static int reject(unsigned ndim, const double *x, void *data, unsigned fdim,
                  double *fval) {
  (void)ndim;
  (void)x;
  (void)data;
  (void)fdim;
  (void)fval;
  return 1;
}

static int check_result(const char *name, int status, double value,
                        double error) {
  if (status != 0) {
    fprintf(stderr, "%s returned status %d\n", name, status);
    return 1;
  }
  if (fabs(value - 0.25) > 1e-8) {
    fprintf(stderr, "%s value %.17g is outside tolerance\n", name, value);
    return 1;
  }
  if (!isfinite(error) || error < 0.0 || error > 1e-8) {
    fprintf(stderr, "%s error estimate %.17g is invalid\n", name, error);
    return 1;
  }
  return 0;
}

int main(void) {
  const double lower[2] = {0.0, 0.0};
  const double upper[2] = {1.0, 1.0};
  double value = 0.0;
  double error = 0.0;
  int failures = 0;
  int status;

  status = hcubature(1, product, NULL, 2, lower, upper, 0, 0.0, 1e-10,
                     ERROR_INDIVIDUAL, &value, &error);
  failures += check_result("hcubature", status, value, error);

  status = pcubature(1, product, NULL, 2, lower, upper, 0, 0.0, 1e-10,
                     ERROR_INDIVIDUAL, &value, &error);
  failures += check_result("pcubature", status, value, error);

  status = hcubature_v(1, product_vectorized, NULL, 2, lower, upper, 0, 0.0,
                       1e-10, ERROR_INDIVIDUAL, &value, &error);
  failures += check_result("hcubature_v", status, value, error);

  status = pcubature_v(1, product_vectorized, NULL, 2, lower, upper, 0, 0.0,
                       1e-10, ERROR_INDIVIDUAL, &value, &error);
  failures += check_result("pcubature_v", status, value, error);

  status = hcubature(1, reject, NULL, 2, lower, upper, 0, 0.0, 1e-10,
                     ERROR_INDIVIDUAL, &value, &error);
  if (status == 0) {
    fputs("hcubature did not propagate callback failure\n", stderr);
    ++failures;
  }

  status = pcubature(1, reject, NULL, 2, lower, upper, 0, 0.0, 1e-10,
                     ERROR_INDIVIDUAL, &value, &error);
  if (status == 0) {
    fputs("pcubature did not propagate callback failure\n", stderr);
    ++failures;
  }

  if (failures != 0) {
    fprintf(stderr, "cubature consumer checks failed: %d\n", failures);
    return 1;
  }
  puts("cubature consumer checks passed: 14 assertions");
  return 0;
}
