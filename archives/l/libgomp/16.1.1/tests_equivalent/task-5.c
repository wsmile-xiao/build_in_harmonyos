/* Equiv-rewrite of upstream task-5.c.
 * #pragma omp parallel/task if(0)/task final(1)/taskyield/taskwait + atomic
 * manually lowered to GOMP ABI.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_taskyield (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define GOMP_TASK_FLAG_FINAL 2

int serr;

static void
inner2 (void *p)			/* nested task if(0) */
{
  if (omp_in_final ())
    { GOMP_atomic_start (); serr = 1; GOMP_atomic_end (); }
}

static void
inner1 (void *p)			/* task if(0) */
{
  if (omp_in_final ())
    { GOMP_atomic_start (); serr = 1; GOMP_atomic_end (); }
  GOMP_task (inner2, NULL, NULL, 0, 0, 0 /*if(0)*/, 0, NULL, 0, NULL);
}

static void
final_child (void *p)		/* task shared(serr) inside final task */
{
  if (!omp_in_final ())
    { GOMP_atomic_start (); serr = 1; GOMP_atomic_end (); }
}

static void
final_task (void *p)		/* task final(1) */
{
  if (!omp_in_final ())
    { GOMP_atomic_start (); serr = 1; GOMP_atomic_end (); }
  GOMP_taskyield ();
  GOMP_taskwait ();
  GOMP_task (final_child, NULL, NULL, 0, 0, 1, 0, NULL, 0, NULL);
}

static void
parallel_body (void *p)		/* parallel shared(serr) */
{
  if (omp_in_final ())
    { GOMP_atomic_start (); serr = 1; GOMP_atomic_end (); }
  GOMP_task (inner1, NULL, NULL, 0, 0, 0 /*if(0)*/, 0, NULL, 0, NULL);
  GOMP_task (final_task, NULL, NULL, 0, 0, 1, GOMP_TASK_FLAG_FINAL,
	     NULL, 0, NULL);
}

int
main (void)
{
  int e;
  GOMP_parallel (parallel_body, NULL, 0, 0);
  GOMP_atomic_start ();
  e = serr;
  GOMP_atomic_end ();
  if (e)
    abort ();
  return 0;
}
