/* Equivalent rewrite: "parallel + single" -> GOMP_parallel + GOMP_single_start */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

static void
body (void *vp)
{
  int *i = (int *) vp;

  if (GOMP_single_start ())
    {
      (*i)++;
    }
  GOMP_barrier ();
}

int
main ()
{
  int i = 0;

  GOMP_parallel (body, &i, 0, 0);

  if (i != 1)
    abort ();

  return 0;
}
