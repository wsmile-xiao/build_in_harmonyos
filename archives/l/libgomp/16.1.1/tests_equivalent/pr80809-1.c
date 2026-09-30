/* PR middle-end/80809 - equiv rewrite. parallel single for task (w[i] = v) ->
 * GOMP_parallel + GOMP_single + GOMP_task; v (VLA) shared, w[i] all == v.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>
#include <stddef.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_barrier (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

struct task_d { int i; int *v; int **w; };

static void
task_body (void *arg)
{
  struct task_d *d = (struct task_d *) arg;
  d->w[d->i] = d->v;
}

struct fctx { int *v; int **w; };

static void
par_body (void *arg)
{
  struct fctx *c = (struct fctx *) arg;
  if (GOMP_single_start ())
    {
      int i;
      for (i = 0; i < 16; i++)
	{
	  struct task_d td = { i, c->v, c->w };
	  GOMP_task (task_body, &td, 0, sizeof (td), _Alignof (struct task_d),
		     1, 0, 0, 0, 0);
	}
    }
  GOMP_barrier ();   /* implicit barrier at end of single */
}

static void
foo (int x)
{
  int v[x], *w[16];
  int i;
  for (i = 0; i < x; i++)
    v[i] = i;
  struct fctx c = { v, w };
  GOMP_parallel (par_body, &c, 0, 0);
  for (i = 0; i < 16; i++)
    if (w[i] != v)
      abort ();
}

int
main (void)
{
  foo (4);
  foo (27);
  foo (196);
  return 0;
}
