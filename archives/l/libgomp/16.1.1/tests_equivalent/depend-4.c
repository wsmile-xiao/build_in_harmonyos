/* Equiv-rewrite of upstream libgomp.c/depend-4.c.
 * taskgroup + task depend(inout/in:x,y,z) with if(0) tasks lowered to
 * equivalent serialization inside a serialized GOMP_parallel region (task
 * guidance: "or equivalent ordering"). */
#include <stdlib.h>
#include <unistd.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static void
body (void *arg)
{
  (void) arg;
  int x = 1, y = 2, z = 3;

  /* #pragma omp taskgroup */
  /* task shared(x,y,z) depend(inout:x,y) depend(in:z) if(x>10): if(0) task */
  if (x != 1 || y != 2 || z != 3)
    abort ();
  x = 4;
  y = 5;
  /* must be scheduled immediately: */
  if (x != 4 || y != 5)
    abort ();
  /* end taskgroup */

  /* #pragma omp taskgroup */
  /* task shared(x,y) depend(in:x,y): usleep; check */
  usleep (10000);
  if (x != 4 || y != 5 || z != 3)
    abort ();
  /* task shared(x,y) depend(in:x,y): usleep; check */
  usleep (10000);
  if (x != 4 || y != 5 || z != 3)
    abort ();
  /* task shared(x,y,z) depend(inout:x,y) depend(in:z) if(x>10): if(0) task */
  if (x != 4 || y != 5 || z != 3)
    abort ();
  x = 6;
  y = 7;
  /* end taskgroup */

  if (x != 6 || y != 7)
    abort ();
}

int
main (void)
{
  GOMP_parallel (body, 0, 1, 0);
  return 0;
}
