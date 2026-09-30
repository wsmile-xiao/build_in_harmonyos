/* Equivalent rewrite: "parallel for ... schedule(static,chunk) firstprivate(first_time)" -> GOMP */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

#define N          50
#define CHUNKSIZE  5

struct ws4_ctx
{
  float *a;
  float *b;
  float *c;
  int chunk;
  char first_time;
};

static void
ws4_body (void *vp)
{
  struct ws4_ctx *d = (struct ws4_ctx *) vp;
  int i, tid;
  char first_time = d->first_time; /* firstprivate */
  long istart, iend;

  if (GOMP_loop_static_start (0, N, 1, d->chunk, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      if (first_time == 'y')
		{
		  tid = omp_get_thread_num ();
		  first_time = 'n';
		}
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
  char first_time;
  struct ws4_ctx ctx;

  for (i = 0; i < N; i++)
    a[i] = b[i] = i * 1.0;
  chunk = CHUNKSIZE;
  first_time = 'y';

  ctx.a = a;
  ctx.b = b;
  ctx.c = c;
  ctx.chunk = chunk;
  ctx.first_time = first_time;

  GOMP_parallel (ws4_body, &ctx, 0, 0);

  return 0;
}
