/* Equiv-rewrite of upstream teams-1.c.
 * #pragma omp teams thread_limit(2) { distribute for(1 iter); parallel } 
 * lowered to GOMP_teams_reg + GOMP_parallel.  Host teams runs N teams serially;
 * the distribute loop (1 iteration, static) is taken only by team 0.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static void
parallel_body (void *p)
{
  if (!omp_in_parallel ()
      || omp_get_level () != 1
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != omp_get_thread_num ()
      || omp_get_ancestor_thread_num (2) != -1)
    abort ();
}

static void
teams_body (void *p)
{
  /* #pragma omp distribute dist_schedule(static,1) for (i=0; i<1; ++i) */
  if (omp_get_team_num () == 0)
    {
      if (omp_in_parallel ()
	  || omp_get_level () != 0
	  || omp_get_ancestor_thread_num (0) != 0
	  || omp_get_ancestor_thread_num (1) != -1)
	abort ();
    }
  GOMP_parallel (parallel_body, NULL, 2, 0);
}

int
main (void)
{
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_teams_reg (teams_body, NULL, 0, 2, 0);	/* teams thread_limit(2) */
  return 0;
}
