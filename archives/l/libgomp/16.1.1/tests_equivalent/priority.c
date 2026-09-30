/* priority - equiv rewrite. task priority + atomic capture/read -> GOMP_task
 * (priority flag) + GOMP_atomic. Requires OMP_MAX_TASK_PRIORITY=10 at run time.
 */
#include <stdlib.h>
#include <omp.h>
#include <stddef.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define GOMP_TASK_FLAG_PRIORITY (1u << 4)
#define N 64

struct task_d { int i; int *tsknum; int *prio; };

static void
task_body (void *arg)
{
  struct task_d *d = (struct task_d *) arg;
  int t;
  GOMP_atomic_start ();
  t = (*d->tsknum)++;
  GOMP_atomic_end ();
  d->prio[t] = d->i ^ 1;
}

struct sd { int *tsknum; int *prio; int *saved; };

static void
single_body (void *arg)
{
  struct sd *d = (struct sd *) arg;
  int i;
  for (i = 0; i < N; i++)
    {
      struct task_d td = { i, d->tsknum, d->prio };
      GOMP_task (task_body, &td, 0, sizeof (td), _Alignof (struct task_d),
		 1, GOMP_TASK_FLAG_PRIORITY, 0, i ^ 1, 0);
    }
  GOMP_atomic_start ();
  *d->saved = *d->tsknum;
  GOMP_atomic_end ();
}

static void
par_body (void *arg)
{
  if (GOMP_single_start ())
    single_body (arg);
}

int
main (void)
{
  int tsknum = 0, prio[N];
  int max_priority = omp_get_max_task_priority ();
  int saved_tsknum = -1;
  int i;
  struct sd d = { &tsknum, prio, &saved_tsknum };
  GOMP_parallel (par_body, &d, 1, 0);
  if (saved_tsknum == 0)
    {
      for (i = 0; i < N; i++)
	if (i < N - max_priority)
	  {
	    if (prio[i] < max_priority)
	      abort ();
	  }
	else if (i != N - prio[i] - 1)
	  abort ();
    }
  return 0;
}
