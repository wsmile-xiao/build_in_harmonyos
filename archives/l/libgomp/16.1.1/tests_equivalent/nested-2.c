/* Equiv-rewrite of upstream nested-2.c.
 * Same as nested-1 but omp_set_nested(0): the inner parallel is serialized to
 * 1 thread by libgomp's GOMP_parallel (max_active_levels=1).
 */
#include <omp.h>
#include <stdlib.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_single_start (void);
extern void GOMP_barrier (void);

struct outer_data { int *i; int *j; };

static void inner_body (void *p)
{
  int *j = (int *) p;
  if (GOMP_single_start ())
    *j = omp_get_thread_num () + omp_get_num_threads () * 256;
  GOMP_barrier ();
}

static void outer_body (void *p)
{
  struct outer_data *d = (struct outer_data *) p;
  if (GOMP_single_start ())
    {
      *d->i = omp_get_thread_num () + omp_get_num_threads () * 256;
      GOMP_parallel (inner_body, d->j, 2, 0);
    }
  GOMP_barrier ();
}

int main (void)
{
  int i = -1, j = -1;
  struct outer_data d = { &i, &j };

  omp_set_nested (0);
  omp_set_dynamic (0);
  GOMP_parallel (outer_body, &d, 4, 0);

  if (i < 4 * 256 || i >= 4 * 256 + 4)
    abort ();
  if (j != 256 + 0)
    abort ();
  return 0;
}
