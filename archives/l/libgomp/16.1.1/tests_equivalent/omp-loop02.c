/* Equivalent rewrite: orphaned "omp for" inside parallel -> GOMP_loop_static */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

#define N 10

static void
parloop (int *a)
{
  int i;
  long istart, iend;

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    a[i] = i + 3;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
par_body (void *vp)
{
  int *a = (int *) vp;
  parloop (a);
}

int
main ()
{
  int i, a[N];

  GOMP_parallel (par_body, a, 0, 0);

  for (i = 0; i < N; i++)
    if (a[i] != i + 3)
      abort ();

  return 0;
}
