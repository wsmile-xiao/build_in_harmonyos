/* PR libgomp/61200 - equiv rewrite. parallel single foo/bar; foo/bar create a
 * task (var=2) and a nested parallel (single sleep); taskwait -> var == 2.
 */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>
#include <stddef.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);

volatile int x;

struct fctx { int *var; };

static void
task_body (void *arg)
{
  struct fctx *c = (struct fctx *) arg;
  sleep (1);
  *c->var = 2;
}

static void
par_body2 (void *arg)
{
  struct fctx *c = (struct fctx *) arg;
  if (x)
    (*c->var)++;
  else if (GOMP_single_start ())
    sleep (2);
}

static void
foo (void)
{
  int var = 1;
  struct fctx fc = { &var };
  /* i = 0: task shared(var) */
  GOMP_task (task_body, &fc, 0, sizeof (fc), _Alignof (struct fctx),
	     1, 0, 0, 0, 0);
  /* i = 1: parallel num_threads(2) */
  GOMP_parallel (par_body2, &fc, 2, 0);
  GOMP_taskwait ();
  if (var != 2)
    abort ();
}

static void
bar (void)
{
  int var = 1;
  struct fctx fc = { &var };
  GOMP_task (task_body, &fc, 0, sizeof (fc), _Alignof (struct fctx),
	     1, 0, 0, 0, 0);
  GOMP_parallel (par_body2, &fc, 2, 0);
  GOMP_taskwait ();
  if (var != 2)
    abort ();
}

struct wctx { int which; };

static void
outer_body (void *arg)
{
  struct wctx *w = (struct wctx *) arg;
  if (GOMP_single_start ())
    {
      if (w->which == 0)
	foo ();
      else
	bar ();
    }
}

int
main (void)
{
  struct wctx w0 = { 0 };
  struct wctx w1 = { 1 };
  omp_set_nested (1);
  GOMP_parallel (outer_body, &w0, 2, 0);
  GOMP_parallel (outer_body, &w1, 2, 0);
  return 0;
}
