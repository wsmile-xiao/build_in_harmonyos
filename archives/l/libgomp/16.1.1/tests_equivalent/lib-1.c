/* Equiv-rewrite of upstream lib-1.c.
 * - 3x #pragma omp parallel reduction(|:l) -> GOMP_parallel + manual reduction.
 * - #pragma omp master -> if (omp_get_thread_num()==0).
 * All other runtime-API calls are already plain libgomp API.
 */
#include <stdlib.h>
#include <omp.h>
#include "libgomp_g.h"

struct data { int *l; };

static void
body1 (void *p)
{
  struct data *d = (struct data *) p;
  int *l = &d->l[omp_get_thread_num ()];
  *l = (omp_get_num_threads () != 3);
  *l |= (omp_get_thread_num () < 0);
  *l |= (omp_get_thread_num () >= 3);
  if (omp_get_thread_num () == 0)   /* master */
    *l |= (omp_get_thread_num () != 0);
}

static void
body2 (void *p)
{
  struct data *d = (struct data *) p;
  d->l[omp_get_thread_num ()] = !omp_in_parallel ();
}

int
main (void)
{
  double dd, e;
  int l;
  omp_lock_t lck;
  omp_nest_lock_t nlck;

  dd = omp_get_wtime ();

  omp_init_lock (&lck);
  omp_set_lock (&lck);
  if (omp_test_lock (&lck))
    abort ();
  omp_unset_lock (&lck);
  if (!omp_test_lock (&lck))
    abort ();
  if (omp_test_lock (&lck))
    abort ();
  omp_unset_lock (&lck);
  omp_destroy_lock (&lck);

  omp_init_nest_lock (&nlck);
  if (omp_test_nest_lock (&nlck) != 1)
    abort ();
  omp_set_nest_lock (&nlck);
  if (omp_test_nest_lock (&nlck) != 3)
    abort ();
  omp_unset_nest_lock (&nlck);
  omp_unset_nest_lock (&nlck);
  if (omp_test_nest_lock (&nlck) != 2)
    abort ();
  omp_unset_nest_lock (&nlck);
  omp_unset_nest_lock (&nlck);
  omp_destroy_nest_lock (&nlck);

  omp_set_dynamic (1);
  if (!omp_get_dynamic ())
    abort ();
  omp_set_dynamic (0);
  if (omp_get_dynamic ())
    abort ();

  omp_set_nested (1);
  if (!omp_get_nested ())
    abort ();
  omp_set_nested (0);
  if (omp_get_nested ())
    abort ();

  omp_set_num_threads (5);
  if (omp_get_num_threads () != 1)
    abort ();
  if (omp_get_max_threads () != 5)
    abort ();
  if (omp_get_thread_num () != 0)
    abort ();
  omp_set_num_threads (3);
  if (omp_get_num_threads () != 1)
    abort ();
  if (omp_get_max_threads () != 3)
    abort ();
  if (omp_get_thread_num () != 0)
    abort ();

  l = 0;
  {
    int nt = omp_get_max_threads ();
    int *l_priv = calloc ((size_t) nt, sizeof (int));
    struct data d = { l_priv };
    int t;
    GOMP_parallel (body1, &d, 0, 0);
    for (t = 0; t < nt; t++)
      l |= l_priv[t];
    free (l_priv);
  }
  if (l)
    abort ();

  if (omp_get_num_procs () <= 0)
    abort ();
  if (omp_in_parallel ())
    abort ();

  {
    int nt = omp_get_max_threads ();
    int *l_priv = calloc ((size_t) nt, sizeof (int));
    struct data d = { l_priv };
    int t;
    GOMP_parallel (body2, &d, 0, 0);
    for (t = 0; t < nt; t++)
      l |= l_priv[t];
    free (l_priv);
  }

  {
    int nt = omp_get_max_threads ();
    int *l_priv = calloc ((size_t) nt, sizeof (int));
    struct data d = { l_priv };
    int t;
    GOMP_parallel (body2, &d, 0, 0);   /* parallel if(1) == normal parallel */
    for (t = 0; t < nt; t++)
      l |= l_priv[t];
    free (l_priv);
  }

  if (l)
    abort ();

  e = omp_get_wtime ();
  if (dd > e)
    abort ();
  dd = omp_get_wtick ();
  if (dd <= 0 || dd > 1)
    abort ();

  return 0;
}
