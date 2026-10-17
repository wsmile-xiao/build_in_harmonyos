/* Equiv-rewrite of upstream lock-2.c.
 * - #pragma omp parallel reduction(+:l) num_threads(1) -> GOMP_parallel(...,1,0).
 * - #pragma omp task if(0) shared(lock,l) -> GOMP_task(..., if_clause=0).
 * - #pragma omp taskwait -> GOMP_taskwait.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

struct data { int l; omp_nest_lock_t *lock; };

static void
task_body (void *p)
{
  struct data *d = (struct data *) p;
  if (omp_test_nest_lock (d->lock) != 0)
    d->l++;
}

static void
parallel_body (void *p)
{
  struct data *d = (struct data *) p;
  if (omp_test_nest_lock (d->lock) != 1)
    d->l++;
  if (omp_test_nest_lock (d->lock) != 2)
    d->l++;
  GOMP_task (task_body, d, NULL, 0, 0, 0, 0, NULL, 0, NULL);
  GOMP_taskwait ();
  if (omp_test_nest_lock (d->lock) != 3)
    d->l++;
  omp_unset_nest_lock (d->lock);
  omp_unset_nest_lock (d->lock);
  omp_unset_nest_lock (d->lock);
}

int
main (void)
{
  struct data d = { 0, NULL };
  omp_nest_lock_t lock;
  omp_init_nest_lock (&lock);
  d.lock = &lock;
  GOMP_parallel (parallel_body, &d, 1, 0);
  if (d.l)
    abort ();
  omp_destroy_nest_lock (&lock);
  return 0;
}
