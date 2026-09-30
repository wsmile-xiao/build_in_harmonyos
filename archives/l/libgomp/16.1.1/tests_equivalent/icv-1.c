/* Equiv-rewrite of upstream icv-1.c.
 * - #pragma omp parallel reduction(|:err) num_threads(1) -> GOMP_parallel(...,1,0).
 * - #pragma omp task if(0) shared(err) -> GOMP_task(..., if_clause=0).
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

struct data { int err; };

static void
task_body (void *p)
{
  struct data *d = (struct data *) p;
  if (omp_get_max_threads () != 6)
    d->err |= 2;
  omp_set_num_threads (5);
  if (omp_get_max_threads () != 5)
    d->err |= 4;
}

static void
parallel_body (void *p)
{
  struct data *d = (struct data *) p;
  if (omp_get_max_threads () != 4)
    d->err |= 1;
  omp_set_num_threads (6);
  GOMP_task (task_body, d, NULL, 0, 0, 0, 0, NULL, 0, NULL);
  if (omp_get_max_threads () != 6)
    d->err |= 8;
}

int
main (void)
{
  struct data d = { 0 };
  omp_set_num_threads (4);
  if (omp_get_max_threads () != 4)
    abort ();
  GOMP_parallel (parallel_body, &d, 1, 0);
  if (d.err)
    abort ();
  if (omp_get_max_threads () != 4)
    abort ();
  return 0;
}
