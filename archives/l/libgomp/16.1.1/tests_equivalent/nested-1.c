/* Equiv-rewrite of upstream nested-1.c.
 * #pragma omp parallel -> GOMP_parallel; #pragma omp single -> GOMP_single_start
 *   + GOMP_barrier (implicit barrier at end of single).
 * Nested parallel (omp_set_nested(1)) is handled by libgomp GOMP_parallel.
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

  omp_set_nested (1);
  omp_set_dynamic (0);
  GOMP_parallel (outer_body, &d, 4, 0);

  if (i < 4 * 256 || i >= 4 * 256 + 4)
    abort ();
  if (j < 2 * 256 || j >= 2 * 256 + 2)
    abort ();
  return 0;
}
