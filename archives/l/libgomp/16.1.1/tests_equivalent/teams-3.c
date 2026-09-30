/* Equivalent rewrite: "teams reduction(+:niters) + distribute collapse(3)" -> GOMP_teams_reg.
 * collapse(3): 3 * 4 * 9 = 108 iterations; each iteration only does niters++. */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

static void
team_fn (void *vp)
{
  int *niters = (int *) vp;
  int c = omp_get_num_teams ();
  int d = omp_get_team_num ();
  int local = 0;
  int t;

  /* distribute (static) over the 108 collapsed iterations */
  for (t = d; t < 108; t += c)
    local++;

  GOMP_atomic_start ();
  *niters += local;
  GOMP_atomic_end ();
}

int
main ()
{
  int niters = 0;

  GOMP_teams_reg (team_fn, &niters, 0, 0, 0);

  if (niters != 108)
    abort ();

  return 0;
}
