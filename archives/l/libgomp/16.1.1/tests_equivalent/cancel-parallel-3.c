/* Equiv-rewrite of upstream libgomp.c/cancel-parallel-3.c.
 * #pragma omp parallel num_threads(16) with barrier/cancellation point/
 * cancel and "for schedule(runtime) nowait" workshares lowered to GOMP ABI.
 * Run with OMP_CANCELLATION=true. */
#include <omp.h>
#include <unistd.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern _Bool GOMP_loop_runtime_start (long, long, long, long *, long *);
extern _Bool GOMP_loop_runtime_next (long *, long *);
extern void GOMP_loop_end_nowait (void);
extern _Bool GOMP_cancel (int, _Bool);
extern _Bool GOMP_cancellation_point (int);

#define GOMP_CANCEL_PARALLEL 1

static inline void
do_some_work (void)
{
  asm volatile ("" : : : "memory");
}

static void
body (void *data)
{
  (void) data;
  long i, istart, iend;
  long j;

  do_some_work ();
  GOMP_barrier ();

  if (omp_get_thread_num () == 1)
    {
      sleep (2);
      if (GOMP_cancellation_point (GOMP_CANCEL_PARALLEL))
	return;
    }

  for (j = 3; j <= 16; j++)
    {
      if (GOMP_loop_runtime_start (0, j, 1, &istart, &iend))
	{
	  do
	    {
	      for (i = istart; i < iend; i++)
		do_some_work ();
	    }
	  while (GOMP_loop_runtime_next (&istart, &iend));
	}
      GOMP_loop_end_nowait ();
    }

  if (omp_get_thread_num () == 0)
    {
      sleep (1);
      if (GOMP_cancel (GOMP_CANCEL_PARALLEL, 1))
	return;
    }
}

int
main (void)
{
  omp_set_dynamic (0);
  omp_set_schedule (omp_sched_static, 1);
  GOMP_parallel (body, 0, 16, 0);
  return 0;
}
