/* PR middle-end/49898 (parallel for + nested parallel for reduction) - equiv rewrite.
 * sum = 450 via nested GOMP_parallel + manual reduction.
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
	    s += j;
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
  long sum = 0;
  struct outer_ctx oc = { &sum_acc };
  sum_acc = 0;
  GOMP_parallel (outer_body, &oc, 0, 0);
  sum += sum_acc;
  if (sum != 450)
    abort ();
  return 0;
}
