/* Equiv-rewrite of upstream task-7.c.
 * #pragma omp task final(1) + nested task + target nowait, manually lowered.
 * On a host-only device the target region runs via host fallback, which
 * resets the thread context so omp_in_final() is false inside it.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

#define GOMP_TASK_FLAG_FINAL 2

static void
target_body (void *p)		/* target nowait body */
{
  if (omp_in_final ())
    abort ();
}

static void
inner_task (void *p)		/* nested task */
{
  if (!omp_in_final ())
    abort ();
  /* target nowait: inside a final task -> synchronous host fallback */
  GOMP_target (0, target_body, NULL, 0, NULL, NULL, NULL);
  if (!omp_in_final ())
    abort ();
  GOMP_taskwait ();
}

static void
outer_task (void *p)		/* task final(1) */
{
  if (!omp_in_final ())
    abort ();
  GOMP_task (inner_task, NULL, NULL, 0, 0, 1, 0, NULL, 0, NULL);
}

int
main (void)
{
  GOMP_task (outer_task, NULL, NULL, 0, 0, 1, GOMP_TASK_FLAG_FINAL,
	     NULL, 0, NULL);
  return 0;
}
