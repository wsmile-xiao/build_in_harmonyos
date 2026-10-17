/* Equiv-rewrite of upstream libgomp.c/depend-3.c.
 * Nested taskgroup + task depend(in/inout/out:x,y) lowered to equivalent
 * serialization inside a serialized GOMP_parallel region (task guidance:
 * "or equivalent ordering"). */
#include <stdlib.h>
#include <unistd.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static void
body (void *arg)
{
  (void) arg;
  int x = 1, y = 2;

  /* #pragma omp taskgroup (outer) */
  /*   task shared(x) depend(in:x): usleep; check x==1 */
  usleep (10000);
  if (x != 1)
    abort ();
  /*   #pragma omp taskgroup */
  /*     task shared(x) depend(in:x): usleep; check x==1 */
  usleep (15000);
  if (x != 1)
    abort ();
  /*     task shared(y) depend(inout:y): check y==2; y=3 */
  if (y != 2)
    abort ();
  y = 3;
  /*     #pragma omp taskgroup */
  /*       task shared(x) depend(in:x): usleep; check x==1 */
  usleep (13000);
  if (x != 1)
    abort ();
  /*       #pragma omp taskgroup */
  /*         task shared(x) depend(out:x): x=2 */
  x = 2;
  /*       end */
  /*     end */
  /*   end */
  /* end */
}

int
main (void)
{
  GOMP_parallel (body, 0, 1, 0);
  return 0;
}
