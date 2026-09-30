/* Equivalent rewrite: "parallel num_threads(64)" + barrier + "for lastprivate(a)" -> GOMP */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

int a;

static void
foo (void)
{
  int i;
  int a_local = 0;
  int own_last = 0;
  long istart, iend;

  a = 30;
  GOMP_barrier ();

  if (GOMP_loop_static_start (0, 1024, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    a_local = i;
	  if (iend == 1024)
	    own_last = 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* lastprivate(a): copy the last iteration's value to the shared a.  */
  if (own_last)
    a = a_local;
  GOMP_barrier ();

  if (a != 1023)
    abort ();
}

static void
par_body (void *data)
{
  (void) data;
  foo ();
}

int
main (void)
{
  GOMP_parallel (par_body, NULL, 64, 0);
  return 0;
}
