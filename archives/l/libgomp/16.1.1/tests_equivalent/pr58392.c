/* PR tree-optimization/58392 - equiv rewrite.
 * parallel for reduction(+:c) + simd reduction(+:c) -> GOMP_parallel + manual reduction.
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

int d[32 * 32];

struct fctx { long *c; int a, b; };

static void
foo_body (void *arg)
{
  struct fctx *x = (struct fctx *) arg;
  long c_priv = 0, jst, jen;
  if (GOMP_loop_static_start (0, x->a, 32, 0, &jst, &jen))
    {
      do
	{
	  long j;
	  for (j = jst; j < jen; j += 32)
	    {
	      long l;
	      for (l = 0; l < x->b; ++l)
		c_priv += d[j + l];
	    }
	}
      while (GOMP_loop_static_next (&jst, &jen));
    }
  GOMP_loop_end ();
  GOMP_atomic_start (); *x->c += c_priv; GOMP_atomic_end ();
}

static int
foo (int a, int b)
{
  long c = 0;
  struct fctx x = { &c, a, b };
  GOMP_parallel (foo_body, &x, 0, 0);
  return (int) c;
}

struct bctx { long *c; int a; };

static void
bar_body (void *arg)
{
  struct bctx *x = (struct bctx *) arg;
  long c_priv = 0, jst, jen;
  if (GOMP_loop_static_start (0, x->a, 1, 0, &jst, &jen))
    {
      do
	{
	  long j;
	  for (j = jst; j < jen; ++j)
	    c_priv += d[j];
	}
      while (GOMP_loop_static_next (&jst, &jen));
    }
  GOMP_loop_end ();
  GOMP_atomic_start (); *x->c += c_priv; GOMP_atomic_end ();
}

static int
bar (int a)
{
  long c = 0;
  struct bctx x = { &c, a };
  GOMP_parallel (bar_body, &x, 0, 0);
  return (int) c;
}

static int
baz (int a)
{
  int j, c = 0;
  for (j = 0; j < a; ++j)
    c += d[j];
  return c;
}

int
main (void)
{
  int i;
  for (i = 0; i < 32 * 32; i++)
    d[i] = (i & 31);
  if (foo (32 * 32, 32) != (31 * 32 / 2) * 32)
    abort ();
  if (bar (32 * 32) != (31 * 32 / 2) * 32)
    abort ();
  if (baz (32 * 32) != (31 * 32 / 2) * 32)
    abort ();
  return 0;
}
