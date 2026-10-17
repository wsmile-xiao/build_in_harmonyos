/* thread-limit-2.c — 完全等价改写 (需 OMP_THREAD_LIMIT=9)
 * parallel + target if(0)→host + teams thread_limit(6) + 三层嵌套 parallel
 *   + atomic capture → GOMP ABI。
 */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned,
			    unsigned);

static int cnt;

static void
l3 (void *d)
{
  int v;
  GOMP_atomic_start ();
  v = ++cnt;
  GOMP_atomic_end ();
  if (v > 6)
    abort ();
  usleep (10000);
  GOMP_atomic_start ();
  --cnt;
  GOMP_atomic_end ();
}

static void
l2 (void *d)
{
  GOMP_parallel (l3, NULL, 2, 0);
}

static void
l1 (void *d)
{
  GOMP_parallel (l2, NULL, 5, 0);
}

static void
tchk3 (void *d)
{
  if (omp_get_thread_limit () > 6
      || (omp_get_thread_limit () == 6 && omp_get_num_threads () != 3))
    abort ();
}

static void
tchk8 (void *d)
{
  if (omp_get_thread_limit () > 6
      || (omp_get_thread_limit () == 6 && omp_get_num_threads () > 6))
    abort ();
}

static void
tchk6 (void *d)
{
  if (omp_get_thread_limit () > 6
      || (omp_get_thread_limit () == 6 && omp_get_num_threads () != 6))
    abort ();
}

static void
teams_fn (void *d)
{
  GOMP_parallel (tchk3, NULL, 3, 0);
  GOMP_parallel (tchk3, NULL, 3, 0);
  GOMP_parallel (tchk8, NULL, 8, 0);
  GOMP_parallel (tchk6, NULL, 6, 0);
  GOMP_parallel (l1, NULL, 5, 0);
}

static void
chk8 (void *d)
{
  if (omp_get_num_threads () != 8)
    abort ();
}

static void
chk16 (void *d)
{
  if (omp_get_num_threads () > 9)
    abort ();
}

int
main (void)
{
  if (omp_get_thread_limit () != 9)
    return 0;
  omp_set_dynamic (0);
  GOMP_parallel (chk8, NULL, 8, 0);
  GOMP_parallel (chk16, NULL, 16, 0);

  /* target if(0) → host 直接执行 */
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_teams_reg (teams_fn, NULL, 0, 6, 0);

  return 0;
}
