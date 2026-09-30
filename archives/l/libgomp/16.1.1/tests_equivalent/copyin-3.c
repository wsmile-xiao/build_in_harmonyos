/* Equiv-rewrite of upstream libgomp.c/copyin-3.c.
 * threadprivate(thr) simulated with a per-thread array; "parallel copyin(thr)"
 * and "parallel reduction(||:l)" lowered to GOMP ABI. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define MAXT 256
static int thr_arr[MAXT];	/* threadprivate thr */

static int
test (int l)
{
  int t = omp_get_thread_num ();
  return l || (thr_arr[t] != t * 2);
}

static void
r1 (void *p)
{
  int *master = p;
  int t = omp_get_thread_num ();
  thr_arr[t] = *master;		/* copyin(thr) */
}

static void
r2 (void *p)
{
  int *lp = p;
  int t = omp_get_thread_num ();
  int myl = thr_arr[t] != 8;

  thr_arr[t] = t * 2;
  GOMP_barrier ();
  myl = test (myl);

  GOMP_atomic_start ();
  *lp |= myl;
  GOMP_atomic_end ();
}

int
main (void)
{
  int l = 0;

  omp_set_dynamic (0);
  omp_set_num_threads (6);

  thr_arr[0] = 8;
  /* Broadcast the value to all threads (copyin). */
  GOMP_parallel (r1, &thr_arr[0], 0, 0);

  GOMP_parallel (r2, &l, 0, 0);

  if (l)
    abort ();
  return 0;
}
