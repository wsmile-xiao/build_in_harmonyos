/* Equivalent rewrite: "parallel ... for schedule(dynamic,chunk)" -> GOMP_loop_dynamic */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

#define CHUNKSIZE 10
#define N         100

struct ws1_ctx
{
  float *a;
  float *b;
  float *c;
  int chunk;
};

static void
ws1_body (void *vp)
{
  struct ws1_ctx *d = (struct ws1_ctx *) vp;
  int tid = omp_get_thread_num ();
  int nthreads, i;
  long istart, iend;

  if (tid == 0)
    {
      nthreads = omp_get_num_threads ();
      printf ("Number of threads = %d\n", nthreads);
    }
  printf ("Thread %d starting...\n", tid);

  if (GOMP_loop_dynamic_start (0, N, 1, d->chunk, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      d->c[i] = d->a[i] + d->b[i];
	      printf ("Thread %d: c[%d]= %f\n", tid, i, d->c[i]);
	    }
	}
      while (GOMP_loop_dynamic_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (int argc, char *argv[])
{
  int i, chunk;
  float a[N], b[N], c[N];
  struct ws1_ctx ctx;

  (void) argc; (void) argv;

  for (i = 0; i < N; i++)
    a[i] = b[i] = i * 1.0;
  chunk = CHUNKSIZE;

  ctx.a = a;
  ctx.b = b;
  ctx.c = c;
  ctx.chunk = chunk;

  GOMP_parallel (ws1_body, &ctx, 0, 0);

  return 0;
}
