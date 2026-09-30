/* Equiv-rewrite of upstream target-30.c.
 * #pragma omp target / target update / parallel private(v) num_threads(1).
 * On host-only, target == host execution (map degenerates to host pointer),
 * target update == no-op; parallel private(v) still creates a new task team.
 */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

int v = 6;	/* was: declare target (irrelevant on host-only) */

static void
parallel_body (void *p)
{
  int v;			/* private (uninitialized) */
  /* #pragma omp target  (predetermined firstprivate(v)); v++ */
  v++;
}

int
main (void)
{
  /* #pragma omp target  (predetermined map(tofrom: v)); v++; */
  v++;
  /* #pragma omp target update from (v)  -- no-op on host-only */
  if (v != 7)
    abort ();
  /* #pragma omp parallel private(v) num_threads(1) { target v++; } */
  GOMP_parallel (parallel_body, NULL, 1, 0);
  /* #pragma omp target update from (v)  -- no-op */
  if (v != 7)
    abort ();
  return 0;
}
