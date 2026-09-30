/* Equiv-rewrite of upstream target-teams-1.c.
 * #pragma omp target / target teams / teams (num_teams, thread_limit) +
 * parallel if(0) manually lowered to GOMP ABI.
 * Host teams runs N teams serially; target on host-only runs via host fallback.
 */
#include <omp.h>
#include <stdlib.h>
#include <limits.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

int v = 6;

void
bar (long *x, long *y)
{
  *x += 2;
  *y += 3;
}

int
baz (void)
{
  return 5;
}

static int g_err;
static unsigned g_nteams, g_thrlim;
static long g_nlim, g_tlim;

static void
tc_par (void *p)		/* parallel if(0): check thread_limit */
{
  if (omp_get_thread_limit () < 1 || omp_get_thread_limit () > g_tlim)
    g_err = 1;
}

static void
tc_body (void *p)		/* teams body: check num_teams, then parallel */
{
  if (omp_get_num_teams () < 1 || omp_get_num_teams () > g_nlim)
    g_err = 1;
  GOMP_parallel (tc_par, NULL, 1, 0);
}

static void
target_teams (void *p)		/* target body: run teams via host fallback */
{
  GOMP_teams_reg (tc_body, NULL, g_nteams, g_thrlim, 0);
}

/* Run one "target { teams ... }" / "target teams ..." block and check err.  */
static void
run_block (unsigned nteams, unsigned thrlim, long nlim, long tlim)
{
  g_err = 0;
  g_nteams = nteams;
  g_thrlim = thrlim;
  g_nlim = nlim;
  g_tlim = tlim;
  GOMP_target (0, target_teams, NULL, 0, NULL, NULL, NULL);
  if (g_err)
    abort ();
}

static void
blockA_body (void *p)		/* target map(from:err) err = num_teams != 1 */
{
  g_err = (omp_get_num_teams () != 1);
}

__attribute__((noinline, noclone)) void
foo (int a, int b, long c, long d)
{
  if (omp_get_num_teams () != 1)
    abort ();

  /* Block A */
  g_err = 0;
  GOMP_target (0, blockA_body, NULL, 0, NULL, NULL, NULL);
  if (g_err)
    abort ();

  /* Block B: target { teams (default) } */
  run_block (0, 0, LONG_MAX, LONG_MAX);
  /* Block C: target teams (default) */
  run_block (0, 0, LONG_MAX, LONG_MAX);
  /* Block D: target { teams num_teams(4) } */
  run_block (4, 0, 4, LONG_MAX);
  /* Block E: target teams num_teams(4) */
  run_block (4, 0, 4, LONG_MAX);
  /* Block F: target { teams thread_limit(7) } */
  run_block (0, 7, LONG_MAX, 7);
  /* Block G: target teams thread_limit(7) */
  run_block (0, 7, LONG_MAX, 7);
  /* Block H: target { teams num_teams(4) thread_limit(8) } */
  run_block (4, 8, 4, 8);
  /* Block I: target teams num_teams(4) thread_limit(8) */
  run_block (4, 8, 4, 8);
  /* Block J: target { teams num_teams(a) thread_limit(b) } */
  run_block (a, b, a, b);
  /* Block K: target teams num_teams(a) thread_limit(b) */
  run_block (a, b, a, b);
  /* Block L: target { teams num_teams(c+1) thread_limit(d-1) } */
  run_block (c + 1, d - 1, c + 1, d - 1);
  /* Block M: target teams num_teams(c+1) thread_limit(d-1) */
  run_block (c + 1, d - 1, c + 1, d - 1);
  /* Block N: target map(always to:c,d) { teams num_teams(c+1) thread_limit(d-1) } */
  run_block (c + 1, d - 1, c + 1, d - 1);

  /* Block O: target data map(to:c,d) { target defaultmap bar(&c,&d);
     target { teams num_teams(c+1) thread_limit(d-1) } } */
  {
    bar (&c, &d);		/* host fallback: modifies c,d directly */
    run_block (c + 1, d - 1, c + 1, d - 1);
  }

  /* Block P: target { teams num_teams(baz()+1) thread_limit(baz()-1) } */
  run_block (baz () + 1, baz () - 1, baz () + 1, baz () - 1);
  /* Block Q: target teams num_teams(baz()+1) thread_limit(baz()-1) */
  run_block (baz () + 1, baz () - 1, baz () + 1, baz () - 1);
  /* Block R: target { teams num_teams(v+1) thread_limit(v-1) } */
  run_block (v + 1, v - 1, v + 1, v - 1);
}

int
main (void)
{
  foo (3, 5, 7, 9);
  return 0;
}
