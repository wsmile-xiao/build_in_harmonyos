/* Equiv-rewrite of upstream omp-parallel-for.c.
 * - #pragma omp parallel for firstprivate(a) lastprivate(a) num_threads(2)
 *   schedule(static) -> GOMP_parallel_loop_static + manual firstprivate/
 *   lastprivate.
 */
#include <stdlib.h>
#include "libgomp_g.h"

struct data { int a_fp; int a_lp; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int a = d->a_fp;   /* firstprivate(a) */
  long istart, iend;
  int has_last = 0;

  if (GOMP_loop_static_start (0, 10, 1, 0, &istart, &iend))
    {
      do
	{
	  long i;
	  for (i = istart; i < iend; i++)
	    a = a + i;
	  has_last = (iend == 10);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  if (has_last)   /* lastprivate(a): thread owning the last iteration */
    d->a_lp = a;
}

int
main (void)
{
  int a = 30;
  struct data d = { a, 0 };

  GOMP_parallel_loop_static (body, &d, 2, 0, 10, 1, 0, 0);

  a = d.a_lp;
  if (a != 65)
    abort ();
  return 0;
}
