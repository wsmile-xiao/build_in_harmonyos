/* Equivalent rewrite: parallel + master + task depend(out/inout:y) -> GOMP_task + GOMP_TASK_FLAG_DEPEND */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>
#include <unistd.h>

#define GOMP_TASK_FLAG_DEPEND (1u << 3)

struct t6_ctx
{
  int *x;
  int *y;
};

static void
t6_task1 (void *vp)
{
  struct t6_ctx *d = (struct t6_ctx *) vp;
  sleep (1);
  *d->x = 1;
  *d->y = 1;
}

static void
t6_task2 (void *vp)
{
  struct t6_ctx *d = (struct t6_ctx *) vp;
  if (*d->x != 1 || *d->y != 1)
    abort ();
  (*d->y)++;
}

static void
make_tasks (struct t6_ctx *d)
{
  void *dep1[3];
  void *dep2[3];

  /* depend(out:y) */
  dep1[0] = (void *) 1;   /* ndepend */
  dep1[1] = (void *) 1;   /* nout (out: + inout:) */
  dep1[2] = d->y;         /* address */

  /* depend(inout:y) */
  dep2[0] = (void *) 1;
  dep2[1] = (void *) 1;
  dep2[2] = d->y;

  GOMP_task (t6_task1, d, NULL, sizeof (*d), __alignof__ (struct t6_ctx), 1,
	     GOMP_TASK_FLAG_DEPEND, dep1, 0, NULL);
  GOMP_task (t6_task2, d, NULL, sizeof (*d), __alignof__ (struct t6_ctx), 1,
	     GOMP_TASK_FLAG_DEPEND, dep2, 0, NULL);
}

static void
t6_body (void *vp)
{
  struct t6_ctx *d = (struct t6_ctx *) vp;
  if (omp_get_thread_num () == 0)  /* master */
    make_tasks (d);
}

int
main ()
{
  int x = 0, y = 0;
  struct t6_ctx ctx;

  ctx.x = &x;
  ctx.y = &y;

  GOMP_parallel (t6_body, &ctx, 0, 0);
  if (x != 1 || y != 2)
    abort ();

  x = 0;
  y = 0;
  GOMP_parallel (t6_body, &ctx, 0, 0);
  if (x != 1 || y != 2)
    abort ();

  return 0;
}
