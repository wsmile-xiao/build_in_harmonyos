/* Equiv-rewrite of upstream teams-4.c.
 * #pragma omp teams/parallel/target/teams lowered to GOMP ABI.  A host-only
 * target region runs via host fallback (thread context reset -> num_teams==1).
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

static void
top_parallel (void *p)
{
  if (omp_get_num_teams () != 1 || omp_get_team_num () != 0)
    abort ();
}

static void
inner_teams (void *p)		/* teams num_teams(2) inside target */
{
  if (omp_get_num_teams () != 2 || (unsigned) omp_get_team_num () >= 2U)
    abort ();
}

static void
target_body (void *p)		/* target (host fallback) */
{
  GOMP_teams_reg (inner_teams, NULL, 2, 0, 0);
}

static void
parallel_if0 (void *p)		/* parallel if(0) */
{
  GOMP_target (0, target_body, NULL, 0, NULL, NULL, NULL);
}

static void
parallel3 (void *p)		/* parallel num_threads(3) */
{
  int *team = p;
  if (omp_get_num_teams () != 4 || omp_get_team_num () != *team)
    abort ();
}

static void
teams4_body (void *p)		/* teams num_teams(4) */
{
  int team = omp_get_team_num ();
  if (omp_get_num_teams () != 4 || (unsigned) team >= 4U)
    abort ();
  GOMP_parallel (parallel3, &team, 3, 0);
  GOMP_parallel (parallel_if0, NULL, 1, 0);
  if (omp_get_num_teams () != 4 || (unsigned) team >= 4U)
    abort ();
}

int
main (void)
{
  if (omp_get_num_teams () != 1 || omp_get_team_num () != 0)
    abort ();
  GOMP_parallel (top_parallel, NULL, 2, 0);
  GOMP_teams_reg (teams4_body, NULL, 4, 0, 0);
  return 0;
}
