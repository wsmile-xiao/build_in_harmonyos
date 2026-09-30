/* critical-2.c — 完全等价改写
 * parallel(shared A,nthreads) + master + for + critical → GOMP ABI。
 */
#include <omp.h>
#include <stdlib.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_critical_start (void);
extern void GOMP_critical_end (void);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define N 2000

struct d
{
  int *A;
  int *nthreads;
};

static void
fn (void *arg)
{
  struct d *d = (struct d *) arg;
  int i;
  long istart, iend;

  /* master */
  if (omp_get_thread_num () == 0)
    *d->nthreads = omp_get_num_threads ();

  /* for (static) */
  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    d->A[i] = 0;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* critical */
  GOMP_critical_start ();
  for (i = 0; i < N; i++)
    d->A[i] += 1;
  GOMP_critical_end ();
}

int
main (void)
{
  int A[N];
  int nthreads;
  int i;
  struct d d = { A, &nthreads };

  GOMP_parallel (fn, &d, 0, 0);

  for (i = 0; i < N; i++)
    if (A[i] != nthreads)
      abort ();

  return 0;
}
