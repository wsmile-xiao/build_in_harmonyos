/* Equiv-rewrite of upstream libgomp.c/cancel-parallel-1.c.
 * #pragma omp parallel num_threads(32) { #pragma omp cancel parallel }
 * manually lowered to GOMP ABI.  Run with OMP_CANCELLATION=true. */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_cancel (int, _Bool);

#define GOMP_CANCEL_PARALLEL 1

static void
body (void *data)
{
  (void) data;
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, 1))
    return;			/* cancellation: leave the parallel region */
  if (omp_get_cancellation ())
    abort ();
}

int
main (void)
{
  GOMP_parallel (body, 0, 32, 0);
  return 0;
}
