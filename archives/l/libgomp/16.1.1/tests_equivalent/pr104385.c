/* PR libgomp/104385 - equiv rewrite. parallel + barrier + master + task with
 * depend(out/inout) -> GOMP_parallel + GOMP_task (depend flag). Final j == 2.
 */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

#define GOMP_TASK_FLAG_DEPEND (1u << 3)

struct jctx { int *j; };

static void
task1_body (void *arg)
{
  struct jctx *x = (struct jctx *) arg;
  usleep (10000);
  *x->j = 1;
}

static void
task2_body (void *arg)
{
  struct jctx *x = (struct jctx *) arg;
  *x->j += 1;
}

static void
outer_task_body (void *arg)
{
  struct jctx *x = (struct jctx *) arg;
  void *dep[3];
  dep[0] = (void *) (uintptr_t) 1;   /* ndepend */
  dep[1] = (void *) (uintptr_t) 1;   /* nout/inout */
  dep[2] = x->j;                     /* &j */
  GOMP_task (task1_body, x, 0, sizeof (*x), _Alignof (struct jctx),
	     1, GOMP_TASK_FLAG_DEPEND, dep, 0, 0);
  GOMP_task (task2_body, x, 0, sizeof (*x), _Alignof (struct jctx),
	     1, GOMP_TASK_FLAG_DEPEND, dep, 0, 0);
}

static void
par_body (void *arg)
{
  struct jctx *x = (struct jctx *) arg;
  GOMP_barrier ();
  if (omp_get_thread_num () == 0)   /* master */
    GOMP_task (outer_task_body, x, 0, sizeof (*x), _Alignof (struct jctx),
	       1, 0, 0, 0, 0);
}

int
main (void)
{
  int j = 0;
  struct jctx x = { &j };
  GOMP_parallel (par_body, &x, 2, 0);
  return j - 2;
}
