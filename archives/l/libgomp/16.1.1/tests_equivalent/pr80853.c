/* PR middle-end/80853 - equiv rewrite.
 * "parallel { for reduction(+:p[:4]) }" -> GOMP_parallel + GOMP_loop_static + manual
 * array-section reduction (per-thread private p[0..3], atomic-combined after).
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static void
foo_body (void *arg)
{
  long *p = (long *) arg;
  long priv[4] = { 0, 0, 0, 0 };
  long ist, ien;
  if (GOMP_loop_static_start (0, 64, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      priv[0] += i;
	      priv[1] += i / 2;
	      priv[2] += 2 * i;
	      priv[3] += 3 * i;
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
  for (int k = 0; k < 4; k++)
    {
      GOMP_atomic_start (); p[k] += priv[k]; GOMP_atomic_end ();
    }
}

static void
foo (long *p)
{
  GOMP_parallel (foo_body, p, 0, 0);
}

int
main (void)
{
  long p[4] = { 0, 0, 0, 0 };
  foo (p);
  if (p[0] != 63L * 64 / 2
      || p[1] != 31L * 32
      || p[2] != 63L * 64
      || p[3] != 3L * 63 * 64 / 2)
    abort ();
  return 0;
}
