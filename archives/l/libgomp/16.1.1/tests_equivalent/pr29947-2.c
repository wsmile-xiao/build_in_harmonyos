/* PR libgomp/29947 (static schedules) - equiv rewrite.
 * parallel { for schedule(static|static,1) [ordered] + reduction(+:e,c) + atomic cnt }
 * -> GOMP_parallel + GOMP_loop_static + manual reduction.
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

int cnt;

struct ctx {
  long j1, k1, j2, k2;
  long start, end, incr;
  long chunk;
  long *e, *c;
  int *cnt;
};

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long e_priv = 0, c_priv = 0;
  long ist, ien;
  if (GOMP_loop_static_start (x->start, x->end, x->incr, x->chunk, &ist, &ien))
    {
      do
	{
	  long i;
	  if (x->incr > 0)
	    for (i = ist; i < ien; i += x->incr)
	      { if (i < x->j2 || i > x->k2) e_priv++; c_priv++; }
	  else
	    for (i = ist; i > ien; i += x->incr)
	      { if (i < x->j2 || i > x->k2) e_priv++; c_priv++; }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
  if (x->cnt)
    { GOMP_atomic_start (); (*x->cnt)++; GOMP_atomic_end (); }
  GOMP_atomic_start (); *x->e += e_priv; GOMP_atomic_end ();
  GOMP_atomic_start (); *x->c += c_priv; GOMP_atomic_end ();
}

static void
run (long j1, long k1, long j2, long k2, long chunk, int ascending, int do_cnt)
{
  long e = 0, c = 0;
  struct ctx x;
  x.j1 = j1; x.k1 = k1; x.j2 = j2; x.k2 = k2;
  if (ascending)
    { x.start = j1; x.end = k1 + 1; x.incr = 1; }
  else
    { x.start = k1; x.end = j1 - 1; x.incr = -1; }
  x.chunk = chunk;
  x.e = &e; x.c = &c; x.cnt = do_cnt ? &cnt : 0;
  GOMP_parallel (body, &x, 0, 0);
  if (e || (c != (j2 > k2 ? 0 : k2 - j2 + 1)))
    abort ();
}

static int
test (long j1, long k1, long j2, long k2)
{
  run (j1, k1, j2, k2, 0, 1, 1);
  run (j1, k1, j2, k2, 0, 0, 1);
  run (j1, k1, j2, k2, 1, 1, 1);
  run (j1, k1, j2, k2, 1, 0, 1);
  run (j1, k1, j2, k2, 0, 1, 1);
  run (j1, k1, j2, k2, 0, 0, 1);
  run (j1, k1, j2, k2, 1, 1, 1);
  run (j1, k1, j2, k2, 1, 0, 1);
  run (j1, k1, j2, k2, 0, 1, 0);
  run (j1, k1, j2, k2, 0, 0, 0);
  run (j1, k1, j2, k2, 1, 1, 0);
  run (j1, k1, j2, k2, 1, 0, 0);
  run (j1, k1, j2, k2, 0, 1, 0);
  run (j1, k1, j2, k2, 0, 0, 0);
  run (j1, k1, j2, k2, 1, 1, 0);
  run (j1, k1, j2, k2, 1, 0, 0);
  return cnt;
}

int
main (void)
{
  test (1, 5, 1, 5);
  test (5, 5, 5, 5);
  test (5, 4, 5, 4);
  test (5, 1, 5, 1);
  return 0;
}
