/* Equiv-rewrite of upstream loop-10.c.
 * - orphaned #pragma omp for -> serial loop with privatized iterator.
 * - #pragma omp parallel private(i) reduction(+:k) -> GOMP_parallel + manual
 *   reduction.
 * - #pragma omp for (worksharing inside parallel) -> GOMP_loop_static_* with a
 *   loop iterator private to the worksharing construct.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

int i = 8;

struct data { int *k; };

static void
parallel_body (void *p)
{
  struct data *d = (struct data *) p;
  int ipriv;   /* private i of the parallel region */
  long istart, iend;

  ipriv = 6;
  /* omp for: worksharing loop, iterator is private to the construct. */
  if (GOMP_loop_static_start (0, 10, 1, 0, &istart, &iend))
    {
      do
	{
	  long loop_i;
	  for (loop_i = istart; loop_i < iend; loop_i++)
	    ;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  d->k[omp_get_thread_num ()] = (ipriv != 6);
}

int
main (void)
{
  int j = 7, k = 0;

  /* orphaned omp for (serial): loop variable is privatized. */
  { int tmp; for (tmp = 0; tmp < 10; tmp++) ; }
  { int tmp; for (tmp = 0; tmp < 10; tmp++) ; }

  if (i != 8 || j != 7)
    abort ();

  {
    int nt = omp_get_max_threads ();
    int *k_priv = calloc ((size_t) nt, sizeof (int));
    struct data d = { k_priv };
    int t;

    GOMP_parallel (parallel_body, &d, 0, 0);

    /* reduction(+:k): combine per-thread copies. */
    k = 0;
    for (t = 0; t < nt; t++)
      k += k_priv[t];
    free (k_priv);
  }

  if (k)
    abort ();
  return 0;
}
