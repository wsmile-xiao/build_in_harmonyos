/* Equiv-rewrite of upstream lock-1.c.
 * #pragma omp parallel if(0) reduction(+:l) is a *serialized parallel region*:
 * it still creates a new task (nest lock is owned by tasks in OpenMP 3.0), so
 * it MUST go through GOMP_parallel with num_threads=1, not a plain serial call.
 */
#include <omp.h>
#include <stdlib.h>
extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

struct data { int l; omp_nest_lock_t *lock; };

static void body (void *p)
{
  struct data *d = (struct data *)p;
  /* reduction(+:l) over 1 thread: shared l fold is equivalent. */
  if (omp_test_nest_lock (d->lock) != 0)
    d->l++;
}

int main (void)
{
  struct data d = { 0, NULL };
  omp_nest_lock_t lock;
  omp_init_nest_lock (&lock);
  d.lock = &lock;
  if (omp_test_nest_lock (&lock) != 1)
    abort ();
  if (omp_test_nest_lock (&lock) != 2)
    abort ();

  /* parallel if(0): serialized but still a new task -> 1 thread team. */
  GOMP_parallel (body, &d, 1, 0);

  if (d.l)
    abort ();
  if (omp_test_nest_lock (&lock) != 3)
    abort ();
  omp_unset_nest_lock (&lock);
  omp_unset_nest_lock (&lock);
  omp_unset_nest_lock (&lock);
  omp_destroy_nest_lock (&lock);
  return 0;
}
