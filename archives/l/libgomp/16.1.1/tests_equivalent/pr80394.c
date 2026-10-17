/* PR libgomp/80394 - equiv rewrite. parallel single { task depend(inout:x) x+=5 ;
 * task if(0) depend(inout:x) ; if(x!=5) abort } -> GOMP_task with depend flag.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdint.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

#define GOMP_TASK_FLAG_DEPEND (1u << 3)

struct ctx { int *x; };

static void
task1_body (void *arg)
{
  struct ctx *c = (struct ctx *) arg;
  for (int i = 0; i < 100000; i++)
    asm volatile ("" ::: "memory");
  *c->x += 5;
}

static void
task2_body (void *arg)
{
  (void) arg;
}

static void
single_body (void *arg)
{
  struct ctx *c = (struct ctx *) arg;
  void *dep[3];
  dep[0] = (void *) (uintptr_t) 1;
  dep[1] = (void *) (uintptr_t) 1;
  dep[2] = c->x;
  GOMP_task (task1_body, c, 0, sizeof (*c), _Alignof (struct ctx),
	     1, GOMP_TASK_FLAG_DEPEND, dep, 0, 0);
  GOMP_task (task2_body, c, 0, 0, 0, 0 /* if(0) */, GOMP_TASK_FLAG_DEPEND, dep, 0, 0);
  if (*c->x != 5)
    abort ();
}

static void
par_body (void *arg)
{
  if (GOMP_single_start ())
    single_body (arg);
}

int
main (void)
{
  int x = 0;
  struct ctx c = { &x };
  GOMP_parallel (par_body, &c, 0, 0);
  return 0;
}
