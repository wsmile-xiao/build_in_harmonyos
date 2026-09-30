/* Equivalent rewrite: parallel + for + critical -> GOMP_parallel/GOMP_loop_static/GOMP_critical */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

#define SIZE 10

struct matvec_ctx
{
  float (*A)[SIZE];
  float *b;
  float *c;
  float *total;
};

static void
matvec_body (void *vp)
{
  struct matvec_ctx *d = (struct matvec_ctx *) vp;
  int tid = omp_get_thread_num ();
  int i, j;
  long istart, iend;

  if (GOMP_loop_static_start (0, SIZE, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      for (j = 0; j < SIZE; j++)
		d->c[i] += (d->A[i][j] * d->b[i]);

	      GOMP_critical_start ();
	      *d->total = *d->total + d->c[i];
	      printf ("  thread %d did row %d\t c[%d]=%.2f\t", tid, i, i, d->c[i]);
	      printf ("Running total= %.2f\n", *d->total);
	      GOMP_critical_end ();
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main ()
{
  float A[SIZE][SIZE], b[SIZE], c[SIZE], total;
  int i, j;
  struct matvec_ctx ctx;

  total = 0.0;
  for (i = 0; i < SIZE; i++)
    {
      for (j = 0; j < SIZE; j++)
	A[i][j] = (j + 1) * 1.0;
      b[i] = 1.0 * (i + 1);
      c[i] = 0.0;
    }

  printf ("\nStarting values of matrix A and vector b:\n");
  for (i = 0; i < SIZE; i++)
    {
      printf ("  A[%d]= ", i);
      for (j = 0; j < SIZE; j++)
	printf ("%.1f ", A[i][j]);
      printf ("  b[%d]= %.1f\n", i, b[i]);
    }
  printf ("\nResults by thread/row:\n");

  ctx.A = A;
  ctx.b = b;
  ctx.c = c;
  ctx.total = &total;

  GOMP_parallel (matvec_body, &ctx, 0, 0);

  printf ("\nMatrix-vector total - sum of all c[] = %.2f\n\n", total);

  return 0;
}
