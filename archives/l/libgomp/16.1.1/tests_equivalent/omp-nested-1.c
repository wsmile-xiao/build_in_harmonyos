/* Equivalent rewrite: nested "parallel for + parallel(num_threads(1)) + atomic" -> GOMP */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

#define N 1000

static void
inner_fn (void *vp)
{
  int *i = (int *) vp;
  GOMP_atomic_start ();
  (*i)++;
  GOMP_atomic_end ();
}

static void
outer_fn (void *vp)
{
  int *i = (int *) vp;
  int j;
  long istart, iend;

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    GOMP_parallel (inner_fn, i, 1, 0);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static int
foo (void)
{
  int i = 0;
  GOMP_parallel (outer_fn, &i, 2, 0);
  return i;
}

int
main (void)
{
  if (foo () != N)
    abort ();
  return 0;
}
