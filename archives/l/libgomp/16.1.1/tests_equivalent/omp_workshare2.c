/* Equivalent rewrite: "parallel ... sections nowait" -> GOMP_sections_* */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

#define N 50

struct ws2_ctx
{
  float *a;
  float *b;
};

static void
ws2_body (void *vp)
{
  struct ws2_ctx *d = (struct ws2_ctx *) vp;
  int tid = omp_get_thread_num ();
  int nthreads, i;
  float c[N];
  unsigned s;

  if (tid == 0)
    {
      nthreads = omp_get_num_threads ();
      printf ("Number of threads = %d\n", nthreads);
    }
  printf ("Thread %d starting...\n", tid);

  s = GOMP_sections_start (2);
  while (s)
    {
      if (s == 1)
	{
	  printf ("Thread %d doing section 1\n", tid);
	  for (i = 0; i < N; i++)
	    {
	      c[i] = d->a[i] + d->b[i];
	      printf ("Thread %d: c[%d]= %f\n", tid, i, c[i]);
	    }
	}
      else if (s == 2)
	{
	  printf ("Thread %d doing section 2\n", tid);
	  for (i = 0; i < N; i++)
	    {
	      c[i] = d->a[i] * d->b[i];
	      printf ("Thread %d: c[%d]= %f\n", tid, i, c[i]);
	    }
	}
      s = GOMP_sections_next ();
    }
  GOMP_sections_end_nowait ();

  printf ("Thread %d done.\n", tid);
}

int
main (int argc, char *argv[])
{
  int i;
  float a[N], b[N];
  struct ws2_ctx ctx;

  (void) argc; (void) argv;

  for (i = 0; i < N; i++)
    a[i] = b[i] = i * 1.0;

  ctx.a = a;
  ctx.b = b;

  GOMP_parallel (ws2_body, &ctx, 0, 0);

  return 0;
}
