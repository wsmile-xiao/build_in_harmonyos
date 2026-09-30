/* Equiv-rewrite of upstream task-reduction-3.c.
 * GNU nested fns -> static fns + pointer args.
 * taskgroup task_reduction(+:i) + task in_reduction(+:i) -> GOMP_taskgroup_* +
 *   GOMP_task over explicit private reduction copies, then manual sum.
 * taskloop reduction(+:j) + nested task in_reduction(+:j) -> same technique.
 * Reduction results are deterministic; + is associative/commutative.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_taskgroup_start (void);
extern void GOMP_taskgroup_end (void);

struct add_ctx { int *x; int val; };
static void add_task (void *p)
{
  struct add_ctx *d = (struct add_ctx *) p;
  *d->x += d->val;
}

/* one taskloop iteration: adds c to its own private j, then a nested
   in_reduction task adds d to a nested private copy. */
struct iter_ctx { int *jit; int *jnest; int c; int d; };
static void iter_task (void *p)
{
  struct iter_ctx *d = (struct iter_ctx *) p;
  *d->jit += d->c;
  {
    struct add_ctx n = { d->jnest, d->d };
    GOMP_task (add_task, &n, 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_taskwait ();
  }
}

static void foo_nested (int *i, int *j) { (*i)++; (*j)++; }

static int foo (void)
{
  int i = -1, j = -1;
  foo_nested (&i, &j);   /* i=0, j=0 */

  /* taskgroup task_reduction(+:i): two in_reduction tasks i++, i+=6 */
  {
    int priv1 = 0, priv2 = 0;
    struct add_ctx t1 = { &priv1, 1 }, t2 = { &priv2, 6 };
    GOMP_taskgroup_start ();
    GOMP_task (add_task, &t1, 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_task (add_task, &t2, 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_taskgroup_end ();
    i += priv1 + priv2;   /* 0 + 1 + 6 = 7 */
  }

  /* taskloop reduction(+:j): 2 iterations, each j+=5 then nested j+=31 */
  {
    int jit[2] = {0, 0}, jnest[2] = {0, 0};
    struct iter_ctx ic[2];
    int k;
    for (k = 0; k < 2; k++)
      { ic[k].jit = &jit[k]; ic[k].jnest = &jnest[k]; ic[k].c = 5; ic[k].d = 31; }
    GOMP_taskgroup_start ();
    GOMP_task (iter_task, &ic[0], 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_task (iter_task, &ic[1], 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_taskgroup_end ();
    j += (jit[0] + jnest[0]) + (jit[1] + jnest[1]);   /* (5+31)*2 = 72 */
  }

  return i + j;   /* 79 */
}

static void bar_nested (int *i, int *j)
{
  /* taskgroup task_reduction(+:i): i++, i+=7 */
  {
    int priv1 = 0, priv2 = 0;
    struct add_ctx t1 = { &priv1, 1 }, t2 = { &priv2, 7 };
    GOMP_taskgroup_start ();
    GOMP_task (add_task, &t1, 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_task (add_task, &t2, 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_taskgroup_end ();
    *i += priv1 + priv2;   /* 0 + 1 + 7 = 8 */
  }

  /* taskloop reduction(+:j): 2 iterations, each j+=21 then nested j+=8 */
  {
    int jit[2] = {0, 0}, jnest[2] = {0, 0};
    struct iter_ctx ic[2];
    int k;
    for (k = 0; k < 2; k++)
      { ic[k].jit = &jit[k]; ic[k].jnest = &jnest[k]; ic[k].c = 21; ic[k].d = 8; }
    GOMP_taskgroup_start ();
    GOMP_task (iter_task, &ic[0], 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_task (iter_task, &ic[1], 0, 0, 0, 1, 0, 0, 0, 0);
    GOMP_taskgroup_end ();
    *j += (jit[0] + jnest[0]) + (jit[1] + jnest[1]);   /* (21+8)*2 = 58 */
  }
}

static int bar (void)
{
  int i = 0, j = 0;
  bar_nested (&i, &j);
  return i + j;   /* 66 */
}

int main (void)
{
  if (foo () != (1 + 6 + (5 + 31) * 2))
    abort ();
  if (bar () != (1 + 7 + (21 + 8) * 2))
    abort ();
  return 0;
}
