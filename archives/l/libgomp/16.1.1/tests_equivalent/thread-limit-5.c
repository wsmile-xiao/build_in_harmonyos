/* Equiv-rewrite of upstream thread-limit-5.c.
 * - #pragma omp teams thread_limit(1) -> GOMP_teams_reg(..., thread_limit=1).
 * - #pragma omp parallel if(0) -> GOMP_parallel(..., num_threads=1).
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

static void
parallel_body (void *data)
{
  (void) data;
  if (omp_get_thread_limit () != 1)
    abort ();
}

static void
teams_body (void *data)
{
  GOMP_parallel (parallel_body, data, 1, 0);
}

int
main (void)
{
  GOMP_teams_reg (teams_body, NULL, 0, 1, 0);
  return 0;
}
