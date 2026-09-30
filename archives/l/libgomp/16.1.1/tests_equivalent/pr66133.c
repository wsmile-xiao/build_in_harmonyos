/* PR middle-end/66133 - equiv rewrite. parallel barrier single task that exits(0).
 */
#include <stdlib.h>
#include <unistd.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

volatile int x;

static void
task_body (void *arg)
{
  (void) arg;
  usleep (2000);
  exit (0);
}

static void
foo (void)
{
  if (x == 0)
    GOMP_task (task_body, 0, 0, 0, 0, 1, 0, 0, 0, 0);
  else
    abort ();
}

static void
par_body (void *arg)
{
  (void) arg;
  GOMP_barrier ();
  if (GOMP_single_start ())
    foo ();
}

int
main (void)
{
  GOMP_parallel (par_body, 0, 2, 0);
  exit (0);
}
