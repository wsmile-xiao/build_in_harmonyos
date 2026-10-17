/* Equiv-rewrite of upstream teams-5.c.
 * #pragma omp teams num_teams(2) { parallel if(0) target } lowered to GOMP ABI.
 * The target's host fallback resets the thread context, so inside it
 * omp_get_num_teams()==1 and omp_get_team_num()==0.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

static void
target_body (void *p)
{
  if (omp_get_num_teams () != 1 || omp_get_team_num () != 0)
    abort ();
}

static void
parallel_if0 (void *p)
{
  GOMP_target (0, target_body, NULL, 0, NULL, NULL, NULL);
}

static void
teams_body (void *p)
{
  if (omp_get_num_teams () != 2)
    abort ();
  GOMP_parallel (parallel_if0, NULL, 1, 0);
}

int
main (void)
{
  GOMP_teams_reg (teams_body, NULL, 2, 0, 0);
  return 0;
}
