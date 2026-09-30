/* Equivalent rewrite of omp_workshare3.c (upstream is a "dg-do compile" negative
 * test demonstrating an invalid parallel-for body block).  Its runtime equivalent
 * is the corrected parallel-for shown here (same computation as omp_workshare4). */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

#define N          50
#define CHUNKSIZE  5

struct ws3_ctx
{
  float *a;
  float *b;
  float *c;
  int chunk;
};

static void
ws3_body (void *vp)
{
  struct ws3_ctx *d = (struct ws3_ctx *) vp;
  int i, tid;
  long istart, iend;

  tid = omp_get_thread_num ();

  if (GOMP_loop_static_start (0, N, 1, d->chunk, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      d->c[i] = d->a[i] + d->b[i];
	      printf ("tid= %d i= %d c[i]= %f\n", tid, i, d->c[i]);
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main ()
{
  int i, chunk;
  float a[N], b[N], c[N];
  struct ws3_ctx ctx;

  for (i = 0; i < N; i++)
    a[i] = b[i] = i * 1.0;
  chunk = CHUNKSIZE;

  ctx.a = a;
  ctx.b = b;
  ctx.c = c;
  ctx.chunk = chunk;

  GOMP_parallel (ws3_body, &ctx, 0, 0);

  return 0;
}
