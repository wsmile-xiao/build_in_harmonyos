/* test_package consumer test for libdogleg 0.18.
 *
 * Solves a 6-parameter nonlinear least-squares problem through the public
 * dense API (dogleg_getDefaultParameters + dogleg_optimize_dense2) and
 * asserts convergence plus recovery of every reference parameter.
 * Math model adapted from upstream sample.c (dense path); deterministic
 * (srandom(0)), 7 assertions total: 1 convergence + 6 parameters.
 */
#include <dogleg.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NSTATE 6
#define GRID_W 10
#define GRID_MIN -10.0
#define GRID_D 2.0
#define NMEAS (GRID_W * GRID_W)

#define REF_A 1.0
#define REF_B 2.0
#define REF_C 3.0
#define REF_D 4.0
#define REF_E 5.0
#define REF_F 6.0

static double s_x[NMEAS];
static double s_y[NMEAS];
static double s_m[NMEAS];

static void make_grid(void)
{
  int i = 0;
  int ix, iy;
  for (ix = 0; ix < GRID_W; ix++)
  {
    double x = GRID_MIN + ix * GRID_D;
    for (iy = 0; iy < GRID_W; iy++)
    {
      double y = GRID_MIN + iy * GRID_D;
      s_x[i] = x;
      s_y[i] = y;
      i++;
    }
  }
}

static void simulate(void)
{
  int i;
  for (i = 0; i < NMEAS; i++)
  {
    double x = s_x[i];
    double y = s_y[i];
    s_m[i] =
      REF_A * REF_B * x * x +
      REF_B * REF_C * y * y +
      REF_C * x * y +
      REF_D * x +
      REF_E * y +
      REF_F +
      ((double)random() / (double)RAND_MAX - 0.5) * 0.2;
  }
}

static void cb_dense(const double *p, double *x, double *J, void *cookie)
{
  int i, k;
  (void)cookie;
  for (i = 0; i < NMEAS; i++)
  {
    double j[NSTATE];
    x[i] =
      p[0] * p[1] * s_x[i] * s_x[i] +
      p[1] * p[2] * s_y[i] * s_y[i] +
      p[2] * s_x[i] * s_y[i] +
      p[3] * s_x[i] +
      p[4] * s_y[i] +
      p[5] - s_m[i];
    j[0] = p[1] * s_x[i] * s_x[i];
    j[1] = p[0] * s_x[i] * s_x[i] + p[2] * s_y[i] * s_y[i];
    j[2] = p[1] * s_y[i] * s_y[i] + s_x[i] * s_y[i];
    j[3] = s_x[i];
    j[4] = s_y[i];
    j[5] = 1.0;
    for (k = 0; k < NSTATE; k++)
      J[i * NSTATE + k] = j[k];
  }
}

int main(void)
{
  static const double ref[NSTATE] = { REF_A, REF_B, REF_C, REF_D, REF_E, REF_F };
  dogleg_parameters2_t params;
  double p[NSTATE];
  double optimum;
  int i, failed = 0, total = 0;

  srandom(0);
  make_grid();
  simulate();

  dogleg_getDefaultParameters(&params);
  params.max_iterations = 8;

  for (i = 0; i < NSTATE; i++)
    p[i] = ((double)random() / (double)RAND_MAX - 0.1) * 1.0;

  optimum = dogleg_optimize_dense2(p, NSTATE, NMEAS, &cb_dense, NULL, &params, NULL);

  total++;
  if (optimum < 0.0)
  {
    printf("ERROR: optimization did not converge\n");
    failed++;
  }
  else
  {
    printf("OK: converged, norm2(x)=%.3f\n", optimum);
  }

  for (i = 0; i < NSTATE; i++)
  {
    double err;
    total++;
    err = fabs(p[i] - ref[i]);
    if (err < 5e-2)
      printf("OK: param %d recovered: got=%.4f want=%.4f err=%.4f\n", i, p[i], ref[i], err);
    else
    {
      printf("ERROR: param %d NOT recovered: got=%.4f want=%.4f err=%.4f\n", i, p[i], ref[i], err);
      failed++;
    }
  }

  printf("ASSERTIONS: %d/%d passed\n", total - failed, total);
  return failed ? 1 : 0;
}
