/* Equiv-rewrite of upstream pr52547.c.
 * - __label__ (declared but unused) removed.
 * - nested function bar (captures y) -> static fn with explicit y arg.
 * - #pragma omp parallel for reduction(|:e) -> GOMP_parallel + static loop
 *   + manual reduction.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

__attribute__((noinline)) static int
bar (int *z, int *y)
{
  return z - y;
}

__attribute__((noinline)) static int
baz (int *x, int *y)
{
  return bar (x, y);
}

struct data { int x; int *y; int *e; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int *e = &d->e[omp_get_thread_num ()];
  long istart, iend;

  if (GOMP_loop_static_start (0, d->x, 1, 0, &istart, &iend))
    {
      do
	{
	  long i;
	  for (i = istart; i < iend; i++)
	    if (baz (&d->y[i], d->y) != i)
	      *e |= 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

__attribute__((noinline)) int
foo (int x, int *y)
{
  int nt = omp_get_max_threads ();
  int *e = calloc ((size_t) nt, sizeof (int));
  struct data d = { x, y, e };
  int res = 0;
  int t;

  GOMP_parallel (body, &d, 0, 0);

  /* reduction(|:e): combine per-thread copies. */
  for (t = 0; t < nt; t++)
    res |= e[t];
  free (e);
  return res;
}

int
main (void)
{
  int a[100], i;
  for (i = 0; i < 100; i++)
    a[i] = i;
  if (foo (100, a))
    abort ();
  return 0;
}
