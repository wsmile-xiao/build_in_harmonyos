/* Equiv-rewrite of upstream pr48591.c.
 * - __float128 -> long double (128-bit quad on aarch64), Q literal -> L.
 * - #pragma omp parallel for reduction(+:f) -> GOMP_parallel + static loop
 *   + manual reduction.
 * - #pragma omp atomic -> GOMP_atomic_start/end.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

struct data { long double *f; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  long double *f = &d->f[omp_get_thread_num ()];
  long istart, iend;

  if (GOMP_loop_static_start (0, 128, 1, 0, &istart, &iend))
    {
      do
	{
	  long i;
	  for (i = istart; i < iend; i++)
	    *f += 0.5L;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  long double f = 0.0L;
  int nt = omp_get_max_threads ();
  long double *f_priv = calloc ((size_t) nt, sizeof (long double));
  struct data d = { f_priv };
  int t;

  GOMP_parallel (body, &d, 0, 0);

  /* reduction(+:f): combine per-thread copies. */
  for (t = 0; t < nt; t++)
    f += f_priv[t];
  free (f_priv);

  if (f != 64.0L)
    abort ();

  GOMP_atomic_start ();
  f += 8.5L;
  GOMP_atomic_end ();

  if (f != 72.5L)
    abort ();
  return 0;
}
