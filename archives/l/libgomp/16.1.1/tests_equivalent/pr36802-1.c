/* PR middle-end/36802 (task within single) - equiv rewrite.
 * parallel { single { if(!k) for(j) task(if j==4 i++) else i++ } } -> GOMP_parallel + GOMP_single + GOMP_task.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>
#include <stddef.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

struct task_d { int j; int *i; };

static void
task_body (void *arg)
{
  struct task_d *d = (struct task_d *) arg;
  if (d->j == 4)
    (*d->i)++;
}

struct foo_ctx { int *i; int k; };

static void
single_body (void *arg)
{
  struct foo_ctx *x = (struct foo_ctx *) arg;
  if (!x->k)
    {
      int j;
      for (j = 0; j < 10; j++)
	{
	  struct task_d td = { j, x->i };
	  GOMP_task (task_body, &td, 0, sizeof (td), _Alignof (struct task_d),
		     1, 0, 0, 0, 0);
	}
    }
  else
    (*x->i)++;
}

static void
par_body (void *arg)
{
  if (GOMP_single_start ())
    single_body (arg);
}

static int
foo (int k)
{
  int i = 0;
  struct foo_ctx x = { &i, k };
  GOMP_parallel (par_body, &x, 0, 0);
  return i;
}

int
main (void)
{
  if (foo (0) != 1)
    abort ();
  if (foo (1) != 1)
    abort ();
  return 0;
}
