/* PR libgomp/29947 (dynamic/guided schedules) - equiv rewrite.
 * parallel { for schedule(dynamic|guided) [ordered] + reduction(+:e,c) + atomic cnt }
 * -> GOMP_parallel + GOMP_loop_dynamic/guided + manual reduction. 'ordered' is a no-op
 * for the observable (c is a sum over iterations).
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_dynamic_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_dynamic_next (long *, long *);
extern bool GOMP_loop_guided_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_guided_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int cnt;

struct ctx {
  long j1, k1, j2, k2;
  long start, end, incr;
  long chunk;
  int sched;   /* 0 = dynamic, 1 = guided */
  long *e, *c;
  int *cnt;
};

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long e_priv = 0, c_priv = 0;
  long ist, ien;
  bool got;
  if (x->sched == 0)
    got = GOMP_loop_dynamic_start (x->start, x->end, x->incr, x->chunk, &ist, &ien);
  else
    got = GOMP_loop_guided_start (x->start, x->end, x->incr, x->chunk, &ist, &ien);
  if (got)
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
	  if (x->sched == 0)
	    got = GOMP_loop_dynamic_next (&ist, &ien);
	  else
	    got = GOMP_loop_guided_next (&ist, &ien);
	}
      while (got);
    }
  GOMP_loop_end ();
  if (x->cnt)
    { GOMP_atomic_start (); (*x->cnt)++; GOMP_atomic_end (); }
  GOMP_atomic_start (); *x->e += e_priv; GOMP_atomic_end ();
  GOMP_atomic_start (); *x->c += c_priv; GOMP_atomic_end ();
}

static void
run (long j1, long k1, long j2, long k2, int sched, int ascending, int do_cnt)
{
  long e = 0, c = 0;
  struct ctx x;
  x.j1 = j1; x.k1 = k1; x.j2 = j2; x.k2 = k2;
  if (ascending)
    { x.start = j1; x.end = k1 + 1; x.incr = 1; }
  else
    { x.start = k1; x.end = j1 - 1; x.incr = -1; }
  x.chunk = 1;
  x.sched = sched;
  x.e = &e; x.c = &c; x.cnt = do_cnt ? &cnt : 0;
  GOMP_parallel (body, &x, 0, 0);
  if (e || (c != (j2 > k2 ? 0 : k2 - j2 + 1)))
    abort ();
}

static int
test (long j1, long k1, long j2, long k2)
{
  /* test1-8: parallel + for (+ordered), atomic cnt */
  run (j1, k1, j2, k2, 0, 1, 1);
  run (j1, k1, j2, k2, 0, 0, 1);
  run (j1, k1, j2, k2, 1, 1, 1);
  run (j1, k1, j2, k2, 1, 0, 1);
  run (j1, k1, j2, k2, 0, 1, 1);
  run (j1, k1, j2, k2, 0, 0, 1);
  run (j1, k1, j2, k2, 1, 1, 1);
  run (j1, k1, j2, k2, 1, 0, 1);
  /* test9-16: parallel for (+ordered), no atomic cnt */
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
