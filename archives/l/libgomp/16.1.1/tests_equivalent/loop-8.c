/* Equiv-rewrite of upstream loop-8.c.
 * schedule(auto) behaves as static in libgomp.  Two constructs:
 *  - `parallel for schedule(auto)` -> GOMP_parallel + GOMP_loop_static.
 *  - `parallel num_threads(4) { foo(); }` with foo() containing an orphaned
 *    `for schedule(auto)` -> GOMP_parallel + worksharing loop inside foo().
 */
#include <omp.h>
#include "libgomp_g.h"

extern void abort (void);

int buf[256];

/* orphaned worksharing loop inside foo(), executed by the active team */
static void
foo (void)
{
  long istart, iend, i;
  if (GOMP_loop_static_start (0, 256, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    buf[i] += i;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
parallel_foo (void *p)
{
  (void) p;
  foo ();
}

static void
parallel_set (void *p)
{
  long istart, iend, i;
  (void) p;
  if (GOMP_loop_static_start (0, 256, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    buf[i] = i;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int i;

  GOMP_parallel (parallel_set, NULL, 0, 0);
  GOMP_parallel (parallel_foo, NULL, 4, 0);

  for (i = 0; i < 256; i++)
    if (buf[i] != 2 * i)
      abort ();
  return 0;
}
