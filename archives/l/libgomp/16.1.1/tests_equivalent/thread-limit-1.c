/* thread-limit-1.c — 完全等价改写 (需 OMP_THREAD_LIMIT=6)
 * parallel + 三层嵌套 parallel + atomic capture → GOMP ABI。
 */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

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
chk3 (void *d)
{
  if (omp_get_num_threads () != 3)
    abort ();
}

static void
chk8 (void *d)
{
  if (omp_get_num_threads () > 6)
    abort ();
}

static void
chk6 (void *d)
{
  if (omp_get_num_threads () != 6)
    abort ();
}

int
main (void)
{
  if (omp_get_thread_limit () != 6)
    return 0;
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_parallel (chk3, NULL, 3, 0);
  GOMP_parallel (chk3, NULL, 3, 0);
  GOMP_parallel (chk8, NULL, 8, 0);
  GOMP_parallel (chk6, NULL, 6, 0);
  GOMP_parallel (l1, NULL, 5, 0);
  return 0;
}
