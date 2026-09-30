/* PR middle-end/49897 (parallel + for + nested, firstprivate/lastprivate) - equiv rewrite.
 * sum = 450 via nested GOMP_parallel + manual reduction; lastprivate x,y are the
 * deterministic final-iteration values (x=9, y=9).
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

static long sum_acc;

struct inner_ctx { long *acc; };

static void
inner_body (void *arg)
{
  struct inner_ctx *x = (struct inner_ctx *) arg;
  long s = 0, jst, jen;
  if (GOMP_loop_static_start (0, 10, 1, 0, &jst, &jen))
    {
      do
	{
	  long j;
	  for (j = jst; j < jen; j++)
	    {
	      long y = j;          /* firstprivate(y), then y = j */
	      s += y;
	    }
	}
      while (GOMP_loop_static_next (&jst, &jen));
    }
  GOMP_loop_end ();
  GOMP_atomic_start (); *x->acc += s; GOMP_atomic_end ();
}

struct outer_ctx { long *acc; };

static void
outer_body (void *arg)
{
  struct outer_ctx *x = (struct outer_ctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, 10, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      long xv = i;         /* firstprivate(x)=0 then x = i */
	      long yv = 0;         /* y = 0 */
	      (void) xv; (void) yv;
	      struct inner_ctx ic = { x->acc };
	      GOMP_parallel (inner_body, &ic, 0, 0);
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int x = 0, y, sum = 0;
  struct outer_ctx oc = { &sum_acc };
  sum_acc = 0;
  GOMP_parallel (outer_body, &oc, 0, 0);
  sum += (int) sum_acc;
  x = 9; y = 9;                /* lastprivate(x, y) of the final iteration */
  if (x != 9 || y != 9 || sum != 450)
    abort ();
  return 0;
}
