/* PR middle-end/42029 - equiv rewrite.
 * "#pragma omp parallel for reduction(+:c)" over a _Complex int -> GOMP_parallel + manual reduction.
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

struct ctx { _Complex int *c; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  _Complex int c_priv = 0;
  long istart, iend;
  if (GOMP_loop_static_start (0, 8, 1, 0, &istart, &iend))
    {
      do
	{
	  long i;
	  for (i = istart; i < iend; i++)
	    c_priv += 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  GOMP_atomic_start ();
  *x->c += c_priv;
  GOMP_atomic_end ();
}

int
main (void)
{
  _Complex int c = 0;
  struct ctx x = { &c };
  GOMP_parallel (body, &x, 0, 0);
  if (c != 8)
    abort ();
  return 0;
}
