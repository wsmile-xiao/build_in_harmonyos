/* Equivalent rewrite: "parallel + single + taskloop reduction(+:r) over [0,c)" with c==0.
 * The taskloop has zero iterations (global c is zero-initialized), so r stays 0. */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

int c;

static void
body (void *vp)
{
  (void) vp;

  if (GOMP_single_start ())
    {
      int r = 0, i;
      /* taskloop reduction(+:r) for (i = 0; i < c; i++) r++;  (c == 0) */
      for (i = 0; i < c; i++)
	r++;
      if (r != 0)
	abort ();
    }
  GOMP_barrier ();
}

int
main ()
{
  GOMP_parallel (body, NULL, 0, 0);
  return 0;
}
