/* Equivalent rewrite: orphaned "omp for reduction(+:sum)" + parallel -> GOMP */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>
#include <stdlib.h>

#define VECLEN 100

float a[VECLEN], b[VECLEN], sum;

static float
dotprod (void)
{
  int i, tid;
  float local = 0.0f;
  long istart, iend;

  tid = omp_get_thread_num ();

  if (GOMP_loop_static_start (0, VECLEN, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      local = local + (a[i] * b[i]);
	      printf ("  tid= %d i=%d\n", tid, i);
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  GOMP_atomic_start ();
  sum = sum + local;
  GOMP_atomic_end ();

  return sum;
}

static void
par_body (void *data)
{
  (void) data;
  sum = dotprod ();
}

int
main (int argc, char *argv[])
{
  int i;
  (void) argc; (void) argv;

  for (i = 0; i < VECLEN; i++)
    a[i] = b[i] = 1.0 * i;
  sum = 0.0;

  GOMP_parallel (par_body, NULL, 0, 0);

  printf ("Sum = %f\n", sum);

  return 0;
}
