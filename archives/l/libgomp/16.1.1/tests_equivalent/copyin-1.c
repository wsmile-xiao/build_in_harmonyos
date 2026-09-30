/* Equiv-rewrite of upstream libgomp.c/copyin-1.c.
 * threadprivate(thr) simulated with a per-thread array; "parallel copyin(thr)
 * reduction(||:l)" lowered to GOMP ABI. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define MAXT 256
static int thr_arr[MAXT];	/* threadprivate thr, indexed by thread number */

struct r1_data { int *master; int *l; };

static void
r1 (void *p)
{
  struct r1_data *d = p;
  int t = omp_get_thread_num ();
  int myl;

  thr_arr[t] = *d->master;	/* copyin(thr) */
  myl = thr_arr[t] != 32;
  thr_arr[t] = t + 11;

  GOMP_atomic_start ();
  *d->l |= myl;
  GOMP_atomic_end ();
}

static void
r2 (void *p)
{
  int *lp = p;
  int t = omp_get_thread_num ();
  int myl = thr_arr[t] != t + 11;

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

  thr_arr[0] = 32;
  {
    int master = thr_arr[0];	/* capture master value before the region */
    struct r1_data d = { &master, &l };
    GOMP_parallel (r1, &d, 0, 0);
  }

  if (l || thr_arr[0] != 11)
    abort ();

  l = 0;
  GOMP_parallel (r2, &l, 0, 0);

  if (l)
    abort ();
  return 0;
}
