/* icv-2.c — 完全等价改写
 * 双 pthread + parallel num_threads(6) reduction(|:l) → GOMP ABI。
 */
#include <pthread.h>
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

pthread_barrier_t bar;

struct d
{
  int pflag;		/* p != NULL */
  int *partials;
};

static void
icv_fn (void *arg)
{
  struct d *d = (struct d *) arg;
  int p = d->pflag;
  int l = 0;
  l |= omp_get_max_threads () != (p ? 3 : 6);
  omp_set_num_threads ((p ? 3 : 6) + omp_get_thread_num ());
  l |= omp_get_max_threads () != ((p ? 3 : 6) + omp_get_thread_num ());
  d->partials[omp_get_thread_num ()] = l;
}

void *
tf (void *p)
{
  int l;
  int maxn, i;
  int *partials;
  struct d d;

  if (p)
    omp_set_num_threads (3);
  pthread_barrier_wait (&bar);
  if (!p)
    omp_set_num_threads (6);
  pthread_barrier_wait (&bar);
  omp_set_dynamic (0);
  if (omp_get_max_threads () != (p ? 3 : 6))
    abort ();

  maxn = omp_get_max_threads ();
  partials = (int *) calloc (maxn, sizeof (int));
  d.pflag = (p != NULL);
  d.partials = partials;
  GOMP_parallel (icv_fn, &d, 6, 0);

  l = 0;
  for (i = 0; i < maxn; i++)
    l |= partials[i];
  free (partials);
  if (l)
    abort ();
  return NULL;
}

int
main (void)
{
  pthread_t th;
  pthread_barrier_init (&bar, NULL, 2);
  pthread_create (&th, NULL, tf, NULL);
  tf ((void *) 1);
  pthread_join (th, NULL);
  return 0;
}
