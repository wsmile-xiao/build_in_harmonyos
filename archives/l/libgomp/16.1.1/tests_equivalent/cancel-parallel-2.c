/* Equiv-rewrite of upstream libgomp.c/cancel-parallel-2.c.
 * #pragma omp parallel firstprivate(x) num_threads(32) with cancel/cancellation
 * point/barrier/task manually lowered to GOMP ABI.  Run with OMP_CANCELLATION=true. */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern _Bool GOMP_barrier_cancel (void);
extern _Bool GOMP_cancel (int, _Bool);
extern _Bool GOMP_cancellation_point (int);

#define GOMP_CANCEL_PARALLEL 1

static void t1 (void *d) { (void) d; usleep (1000); }
static void t2 (void *d) { (void) d; usleep (2000); }
static void t3 (void *d) { (void) d; usleep (4000); }

static void
body (void *p)
{
  int *x = *(int **) p;		/* firstprivate(x): copy of the pointer */
  int thr = omp_get_thread_num ();

  switch (x[thr])
    {
    case 4:
      if (GOMP_cancel (GOMP_CANCEL_PARALLEL, 1))
	return;
      break;
    case 3:
      GOMP_task (t1, 0, 0, 0, 0, 1, 0, 0, 0, 0);
      GOMP_task (t2, 0, 0, 0, 0, 1, 0, 0, 0, 0);
      GOMP_task (t3, 0, 0, 0, 0, 1, 0, 0, 0, 0);
      break;
    case 2:
      usleep (1000);
      /* FALLTHRU */
    case 1:
      if (GOMP_cancellation_point (GOMP_CANCEL_PARALLEL))
	return;
      break;
    default:
      break;
    }

  /* #pragma omp barrier is an implicit cancellation point for the parallel
     region; lower to a cancellable barrier. */
  if (GOMP_barrier_cancel ())
    return;
  if (omp_get_cancellation ())
    abort ();
}

static void
foo (int *x)
{
  GOMP_parallel (body, &x, 32, 0);
}

int
main (void)
{
  int i, j, x[32] = { 0, 1, 2, 4, 2, 2, 1, 0 };

  foo (x);
  for (i = 0; i < 32; i++)
    {
      for (j = 0; j < 32; j++)
	x[j] = rand () & 3;
      x[rand () & 31] = 4;
      foo (x);
    }
  return 0;
}
