/* Equiv-rewrite of upstream libgomp.c/depend-5.c.
 * Chains of task depend(in/inout/out:x,y,z) plus "task if(ifval)" lowered to
 * equivalent serialization inside a serialized GOMP_parallel region (task
 * guidance: "or equivalent ordering"). */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

struct d5 { int ifval; };

static void
f1_body (void *arg)
{
  int ifval = ((struct d5 *) arg)->ifval;
  int x = 1, y = 2, z = 3;

  /* single-region body, serialized (tasks in program order): */
  x = 2;				/* task depend(out:x) */
  if (x != 2)				/* task depend(inout:x) */
    abort ();
  x = 3;
  if (x != 3)				/* task depend(inout:x) */
    abort ();
  x = 4;
  if (z != 3) abort ();			/* 6 x task depend(in:z) */
  if (z != 3) abort ();
  if (z != 3) abort ();
  if (z != 3) abort ();
  if (z != 3) abort ();
  if (z != 3) abort ();
  if (y != 2) abort ();			/* 4 x task depend(in:y) */
  if (y != 2) abort ();
  if (y != 2) abort ();
  if (y != 2) abort ();
  /* task if(ifval) shared(x,y) depend(in:x) depend(inout:y) */
  if (x != 4 || y != 2)
    abort ();
  y = 3;
  if (ifval == 0)
    {
      /* the if(0) task ran synchronously, so y is already 3 */
      if (x != 4 || y != 3)
	abort ();
      x = 5;
      y = 4;
    }
  if (z != 3) abort ();			/* task depend(inout:z) */
  z = 4;
  if (z != 4) abort ();			/* task depend(inout:z) */
  z = 5;
  /* #pragma omp taskwait */
  if (x != (ifval ? 4 : 5) || y != (ifval ? 3 : 4) || z != 5)
    abort ();
  /* task if(ifval) shared(x,y) depend(in:x) depend(inout:y) */
  if (x != (ifval ? 4 : 5) || y != (ifval ? 3 : 4))
    abort ();
}

__attribute__((noinline, noclone)) static void
f1 (int ifval)
{
  struct d5 d = { ifval };
  GOMP_parallel (f1_body, &d, 1, 0);
}

int
main (void)
{
  f1 (0);
  f1 (1);
  return 0;
}
