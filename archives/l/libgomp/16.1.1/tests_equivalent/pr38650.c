/* PR c++/38650 - equiv rewrite.
 * "#pragma omp parallel for reduction(+:e)" -> GOMP_parallel + GOMP_loop_static + manual reduction.
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

static int e;

struct ctx { int *e; long n; };

static void
body (void *arg)
{
  struct ctx *c = (struct ctx *) arg;
  int e_priv = 0;
  long istart, iend;
  if (GOMP_loop_static_start (0, c->n, 1, 0, &istart, &iend))
    {
      do
	{
	  long i;
	  for (i = istart; i < iend; i++)
	    e_priv++;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  GOMP_atomic_start ();
  *c->e += e_priv;
  GOMP_atomic_end ();
}

static void
run (long n)
{
  struct ctx c = { &e, n };
  GOMP_parallel (body, &c, 0, 0);
}

int
main (void)
{
  volatile int j = 10;
  e = 0; run (j); if (e != 10) abort ();
  e = 0; run (j); if (e != 10) abort ();
  e = 0; run (j); if (e != 10) abort ();
  e = 0; run (10); if (e != 10) abort ();
  e = 0; run (10); if (e != 10) abort ();
  e = 0; run (10); if (e != 10) abort ();
  return 0;
}
