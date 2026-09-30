/* Equiv-rewrite of upstream pr81687-2.c.
 * - __label__ + nested functions that computed-goto to immediately following
 *   labels -> static functions returning a flag (goto to next stmt is a no-op).
 * - #pragma omp parallel -> GOMP_parallel; #pragma omp task -> GOMP_task.
 */
#include <omp.h>
#include "libgomp_g.h"

static int foo (int x) { return x == 1; }
static int bar (int x) { return x == 2; }
static int baz (int x) { return x == 3; }

static void
parallel_body (void *data)
{
  int m = *(int *) data;
  int r = foo (m + 1);  /* was: if (x==1) goto lab4;  lab4 is right here */
  (void) r;
}

static void
task_body (void *data)
{
  int m = *(int *) data;
  int r = bar (m + 2);  /* was: if (x==2) goto lab5 */
  (void) r;
}

int
main (void)
{
  volatile int l = 0;
  int m = l;

  GOMP_parallel (parallel_body, &m, 0, 0);

  GOMP_task (task_body, &m, NULL, 0, 0, 1, 0, NULL, 0, NULL);
  GOMP_taskwait ();

  {
    int r = baz (m + 3);  /* was: if (x==3) goto lab6 */
    (void) r;
  }

  return 0;
}
