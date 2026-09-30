/* nqueens-1.c — 完全等价改写
 * threadprivate(cnt) → __thread；#pragma omp task → GOMP_task；
 * parallel reduction(+:tempcnt) + single → GOMP_parallel + GOMP_single_start + 手动归约。
 */
#include <omp.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_barrier (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);

static __thread int cnt = 0;

void nqueens (char *a, int n, int pos);

struct nq_task
{
  int n;
  int pos;
  char b[];
};

static void
nq_task_fn (void *arg)
{
  struct nq_task *t = (struct nq_task *) arg;
  nqueens (t->b, t->n, t->pos);
}

void
nqueens (char *a, int n, int pos)
{
  char b[pos + 1];
  int i, j;
  memcpy (b, a, pos);
  for (i = 0; i < n; i++)
    {
      for (j = 0; j < pos; j++)
	if (b[j] == i || b[j] == i + pos - j || i == b[j] + pos - j)
	  break;
      if (j < pos)
	continue;
      if (pos == n - 1)
	++cnt;
      else
	{
	  size_t sz = sizeof (struct nq_task) + (size_t) (pos + 1);
	  struct nq_task *t = (struct nq_task *) malloc (sz);
	  b[pos] = i;
	  t->n = n;
	  t->pos = pos + 1;
	  memcpy (t->b, b, (size_t) (pos + 1));
	  GOMP_task (nq_task_fn, t, NULL, (long) sz,
		     __alignof__ (struct nq_task), 1, 0, NULL, 0, NULL);
	  free (t);
	}
    }
}

static void
zero_fn (void *d)
{
  cnt = 0;
}

struct red_data
{
  int n;
  int *partials;
};

static void
red_fn (void *arg)
{
  struct red_data *d = (struct red_data *) arg;
  if (GOMP_single_start ())
    nqueens ("", d->n, 0);
  GOMP_barrier ();
  d->partials[omp_get_thread_num ()] = cnt;
}

int
main (int argc, char **argv)
{
  int n = 8;
  if (argc >= 2)
    n = strtoul (argv[1], NULL, 0);
  if (n < 1 || n > 127)
    {
      fprintf (stderr, "invalid count %d\n", n);
      return 1;
    }
  cnt = 0;
  double stime = omp_get_wtime ();
  nqueens ("", n, 0);
  printf ("serial   N %d solutions # %d time %f\n", n, cnt,
	  omp_get_wtime () - stime);

  GOMP_parallel (zero_fn, NULL, 0, 0);
  stime = omp_get_wtime ();
  int tempcnt = 0;
  int maxn = omp_get_max_threads ();
  int *partials = (int *) calloc (maxn, sizeof (int));
  struct red_data d = { n, partials };
  GOMP_parallel (red_fn, &d, 0, 0);
  for (int i = 0; i < maxn; i++)
    tempcnt += partials[i];
  free (partials);
  cnt = tempcnt;
  printf ("parallel N %d solutions # %d time %f\n", n, cnt,
	  omp_get_wtime () - stime);
  return 0;
}
