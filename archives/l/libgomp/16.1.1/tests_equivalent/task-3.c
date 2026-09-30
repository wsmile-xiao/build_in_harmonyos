/* Equivalent rewrite: parallel(4) + task firstprivate/shared + critical + taskwait -> GOMP */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

int l = 5;

struct task3_data
{
  int i;    /* firstprivate */
  int *j;   /* shared */
  int *l;   /* shared (global) */
  int k;    /* firstprivate const (value) */
};

static void
task3_fn (void *vp)
{
  struct task3_data *d = (struct task3_data *) vp;

  GOMP_critical_start ();
  *d->j += d->i;
  *d->l += d->k;
  GOMP_critical_end ();
}

static int
foo (int i)
{
  int j = 7;
  const int k = 8;
  struct task3_data td[4];
  int t;

  for (t = 0; t < 4; t++)
    {
      td[t].i = i;
      td[t].j = &j;
      td[t].l = &l;
      td[t].k = k;
      GOMP_task (task3_fn, &td[t], NULL, sizeof (struct task3_data),
		 __alignof__ (struct task3_data), 1, 0, NULL, 0, NULL);
      i++;
    }

  GOMP_taskwait ();

  return (i != 8 * omp_get_thread_num () + 4
	  || j != 4 * i - 3
	  || k != 8);
}

static void
main_fn (void *vp)
{
  int *r = (int *) vp;

  if (omp_get_num_threads () != 4)
    {
      if (omp_get_thread_num () == 0)  /* master */
	l = 133;
    }
  else if (foo (8 * omp_get_thread_num ()))
    {
      GOMP_atomic_start ();
      (*r)++;
      GOMP_atomic_end ();
    }
}

int
main (void)
{
  int r = 0;

  GOMP_parallel (main_fn, &r, 4, 0);

  if (r || l != 133)
    abort ();

  return 0;
}
