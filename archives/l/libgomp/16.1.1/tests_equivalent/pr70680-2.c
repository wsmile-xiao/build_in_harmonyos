/* PR middle-end/70680 - equiv rewrite. task if(0) + simd collapse(2)/lastprivate
 * -> GOMP_task(if_clause=0); i,j end at 10, v = i + j = 20.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

int v;

struct ctx { int *i; int *j; int set_v; };

static void
task_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  int i, j;
  for (i = 0; i < 10; i++)
    for (j = 0; j < 10; j++)
      ;
  *x->i = i;
  *x->j = j;
  if (x->set_v)
    v = i + j;
}

static void
f1 (void)
{
  int i = 0, j = 0;
  struct ctx x = { &i, &j, 1 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 10 || j != 10)
    abort ();
}

static void
f2 (void)
{
  int i = 0, j = 0;
  struct ctx x = { &i, &j, 0 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 10 || j != 10)
    abort ();
}

static void
f3 (void)
{
  int i = 0, j = 0;
  struct ctx x = { &i, &j, 1 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 10 || j != 10)
    abort ();
}

static void
f4 (void)
{
  int i = 0, j = 0;
  struct ctx x = { &i, &j, 0 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 10 || j != 10)
    abort ();
}

int
main (void)
{
  f1 ();
  if (v++ != 20)
    abort ();
  f2 ();
  f3 ();
  if (v++ != 20)
    abort ();
  f4 ();
  return 0;
}
