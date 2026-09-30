/* Equivalent rewrite: "parallel for reduction(+:sum)" -> GOMP_parallel + static loop + manual reduction */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

struct red_ctx
{
  float *a;
  float *b;
  float *sum;
  int n;
};

static void
red_body (void *vp)
{
  struct red_ctx *d = (struct red_ctx *) vp;
  int i;
  float local = 0.0f;
  long istart, iend;

  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    local = local + (d->a[i] * d->b[i]);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  GOMP_atomic_start ();
  *d->sum = *d->sum + local;
  GOMP_atomic_end ();
}

int
main (int argc, char *argv[])
{
  int i, n;
  float a[100], b[100], sum;
  struct red_ctx ctx;

  (void) argc; (void) argv;

  n = 100;
  for (i = 0; i < n; i++)
    a[i] = b[i] = i * 1.0;
  sum = 0.0;

  ctx.a = a;
  ctx.b = b;
  ctx.sum = &sum;
  ctx.n = n;

  GOMP_parallel (red_body, &ctx, 0, 0);

  printf ("   Sum = %f\n", sum);

  return 0;
}
