/* Equiv-rewrite of upstream target-5.c.
 * #pragma omp target if(0) (+ nested teams/parallel if(0)) manually lowered.
 * target if(0) on host-only == host fallback, which resets the ICV context
 * to initial values (the exact behavior this test checks); reproduced via
 * GOMP_target.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

/* firstprivate (read-only) captured ICV values from the enclosing scope */
static int g_d_o, g_n_o, g_m_o, g_c_o;
static omp_sched_t g_s_o;

static void
target1_body (void *p)
{
  omp_sched_t s_c;
  int c_c;
  omp_get_schedule (&s_c, &c_c);
  if (g_d_o != omp_get_dynamic ()
      || g_n_o != omp_get_nested ()
      || g_s_o != s_c
      || g_c_o != c_c
      || g_m_o != omp_get_max_threads ())
    abort ();
  omp_set_dynamic (0);
  omp_set_nested (0);
  omp_set_schedule (omp_sched_dynamic, 4);
  omp_set_num_threads (2);
  if (!omp_is_initial_device ())
    abort ();
}

static void
parallel_body (void *p)
{
  omp_sched_t s_c;
  int c_c;
  omp_get_schedule (&s_c, &c_c);
  if (g_d_o != omp_get_dynamic ()
      || g_n_o != omp_get_nested ()
      || g_s_o != s_c
      || g_c_o != c_c
      || g_m_o != omp_get_max_threads ())
    abort ();
  omp_set_dynamic (0);
  omp_set_nested (0);
  omp_set_schedule (omp_sched_dynamic, 4);
  omp_set_num_threads (2);
  if (!omp_is_initial_device ())
    abort ();
}

static void
teams_body (void *p)
{
  GOMP_parallel (parallel_body, p, 1, 0);	/* parallel if(0) */
}

int
main (void)
{
  g_d_o = omp_get_dynamic ();
  g_n_o = omp_get_nested ();
  omp_get_schedule (&g_s_o, &g_c_o);
  g_m_o = omp_get_max_threads ();
  omp_set_dynamic (1);
  omp_set_nested (1);
  omp_set_schedule (omp_sched_static, 2);
  omp_set_num_threads (4);
  int d = omp_get_dynamic ();
  int n = omp_get_nested ();
  omp_sched_t s;
  int c;
  omp_get_schedule (&s, &c);
  int m = omp_get_max_threads ();
  if (!omp_is_initial_device ())
    abort ();

  /* #pragma omp target if(0) { ... } */
  GOMP_target (0, target1_body, NULL, 0, NULL, NULL, NULL);

  if (!omp_is_initial_device ())
    abort ();
  omp_sched_t s_c;
  int c_c;
  omp_get_schedule (&s_c, &c_c);
  if (d != omp_get_dynamic ()
      || n != omp_get_nested ()
      || s != s_c
      || c != c_c
      || m != omp_get_max_threads ())
    abort ();

  /* #pragma omp target if(0) teams parallel if(0) { ... } */
  GOMP_target (0, teams_body, NULL, 0, NULL, NULL, NULL);

  if (!omp_is_initial_device ())
    abort ();
  omp_get_schedule (&s_c, &c_c);
  if (d != omp_get_dynamic ()
      || n != omp_get_nested ()
      || s != s_c
      || c != c_c
      || m != omp_get_max_threads ())
    abort ();
  return 0;
}
