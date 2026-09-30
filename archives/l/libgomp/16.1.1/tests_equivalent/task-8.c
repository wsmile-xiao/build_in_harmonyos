/* Equivalent rewrite: top-level task + target(host) + taskwait -> GOMP_task + GOMP_taskwait */
#include <omp.h>
#include "libgomp_g.h"

static void
task8_fn (void *data)
{
  int i;         /* private(i) */
  (void) data;

  /* #pragma omp target nowait private(i) — host: set private i */
  i = 1;

  GOMP_taskwait ();
}

int
main ()
{
  int i = 0;
  (void) i;

  GOMP_task (task8_fn, NULL, NULL, 0, 0, 1, 0, NULL, 0, NULL);

  return 0;
}
