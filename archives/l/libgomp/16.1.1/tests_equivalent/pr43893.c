/* PR c/43893 - equiv rewrite.
 * "#pragma omp parallel for reduction(+:c)" with tricky unsigned/INT_MIN/INT_MAX
 * loop bounds (each loop runs exactly one iteration) -> GOMP_parallel + manual reduction,
 * passing the exact canonical (start,end,incr) to GOMP_loop_static_start.
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

static int c;

struct ctx { int *c; long start, end, incr; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  int c_priv = 0;
  long istart, iend;
  if (GOMP_loop_static_start (x->start, x->end, x->incr, 0, &istart, &iend))
    {
      do
	{
	  long k;
	  if (x->incr > 0)
	    for (k = istart; k < iend; k += x->incr)
	      c_priv++;
	  else
	    for (k = istart; k > iend; k += x->incr)
	      c_priv++;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  GOMP_atomic_start ();
  *x->c += c_priv;
  GOMP_atomic_end ();
}

static void
run (long s, long e, long inc)
{
  struct ctx x = { &c, s, e, inc };
  c = 0;
  GOMP_parallel (body, &x, 0, 0);
  if (c != 1)
    abort ();
}

int
main (void)
{
  /* for (unsigned i = 0; i < 1; i++) */
  run (0, 1, 1);
  /* for (unsigned i = 0; i <= 0; i++) */
  run (0, 1, 1);
  /* for (int j = -INT_MAX-1; j < -INT_MAX; j++)  [j = INT_MIN] */
  run (-2147483647L - 1, -2147483647L, 1);
  /* for (int j = INT_MIN; j <= INT_MIN; j++) */
  run (-2147483647L - 1, -2147483647L, 1);
  /* for (unsigned i = 2U*INT_MAX+1; i > 2U*INT_MAX; i--)  [i = UINT_MAX] */
  run (4294967295L, 4294967294L, -1);
  /* for (unsigned i = 2U*INT_MAX+1; i >= 2U*INT_MAX+1; i--) */
  run (4294967295L, 4294967294L, -1);
  /* for (int j = INT_MAX; j > INT_MAX-1; j--) */
  run (2147483647L, 2147483646L, -1);
  /* for (int j = INT_MAX; j >= INT_MAX; j--) */
  run (2147483647L, 2147483646L, -1);
  return 0;
}
