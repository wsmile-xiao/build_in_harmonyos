/* PR middle-end/70680 - equiv rewrite. task if(0) (undeferred, synchronous) with
 * simd/linear loop -> GOMP_task(if_clause=0); i ends at 100.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

int v;

struct ctx { int *i; int set_v; };

static void
task_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  int *i = x->i;
  for (*i = 0; *i < 100; (*i)++)
    ;
  if (x->set_v)
    v = *i;
}

static void
f1 (void)
{
  int i = 0;
  struct ctx x = { &i, 1 };
  GOMP_task (task_body, &x, 0, 0, 0, 0 /* if(0) */, 0, 0, 0, 0);
  if (i != 100)
    abort ();
}

static void
f2 (void)
{
  int i = 0;
  struct ctx x = { &i, 0 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 100)
    abort ();
}

static void
f3 (void)
{
  int i = 0;
  struct ctx x = { &i, 1 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 100)
    abort ();
}

static void
f4 (void)
{
  int i = 0;
  struct ctx x = { &i, 0 };
  GOMP_task (task_body, &x, 0, 0, 0, 0, 0, 0, 0, 0);
  if (i != 100)
    abort ();
}

int
main (void)
{
  f1 ();
  if (v++ != 100)
    abort ();
  f2 ();
  f3 ();
  if (v++ != 100)
    abort ();
  f4 ();
  return 0;
}
