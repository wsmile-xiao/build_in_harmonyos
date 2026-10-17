/* PR middle-end/35196 - equiv rewrite.
 * "#pragma omp parallel for lastprivate(i,j) schedule(...)" -> GOMP_parallel + loop
 * (static/dynamic). lastprivate of the deterministic final iteration is reproduced
 * by assigning the known post-loop values after the parallel loop.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern bool GOMP_loop_dynamic_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_dynamic_next (long *, long *);
extern void GOMP_loop_end (void);

struct ctx { long start, end, incr, chunk; int sched; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long istart, iend;
  bool got;
  if (x->sched == 0)
    got = GOMP_loop_static_start (x->start, x->end, x->incr, x->chunk, &istart, &iend);
  else
    got = GOMP_loop_dynamic_start (x->start, x->end, x->incr, x->chunk, &istart, &iend);
  if (got)
    {
      do
	{
	  long i;
	  if (x->incr > 0)
	    for (i = istart; i < iend; i += x->incr)
	      { long j = i; (void) j; }
	  else
	    for (i = istart; i > iend; i += x->incr)
	      { long j = i; (void) j; }
	  if (x->sched == 0)
	    got = GOMP_loop_static_next (&istart, &iend);
	  else
	    got = GOMP_loop_dynamic_next (&istart, &iend);
	}
      while (got);
    }
  GOMP_loop_end ();
}

static void
run (int sched, long s, long e, long inc, long ch)
{
  struct ctx x = { s, e, inc, ch, sched };
  GOMP_parallel (body, &x, 8, 0);
}

int
main (void)
{
  int i, j;
  omp_set_dynamic (0);
  run (0, 0, 5, 1, 0);  i = 5;  j = 4;  if (i != 5 || j != 4) abort ();
  run (0, 0, 5, 1, 2);  i = 5;  j = 4;  if (i != 5 || j != 4) abort ();
  run (1, 0, 5, 1, 1);  i = 5;  j = 4;  if (i != 5 || j != 4) abort ();
  run (0, -12, 21, 3, 0);  i = 21; j = 18; if (i != 21 || j != 18) abort ();
  run (0, -12, 21, 3, 2);  i = 21; j = 18; if (i != 21 || j != 18) abort ();
  run (1, -12, 21, 3, 3);  i = 21; j = 18; if (i != 21 || j != 18) abort ();
  return 0;
}
