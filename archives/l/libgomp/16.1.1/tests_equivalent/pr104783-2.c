/* PR libgomp/104783-2 - equiv rewrite. target + parallel for simd + atomic update
 * -> GOMP_parallel + GOMP_loop_static + GOMP_atomic; v == N.
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

#define N (32 * 32)

struct ctx { float *v; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, N, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      GOMP_atomic_start ();
	      *x->v = *x->v + 1.0f;
	      GOMP_atomic_end ();
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  float v = 0.0f;
  struct ctx x = { &v };
  GOMP_parallel (body, &x, 0, 0);
  if (v != N)
    abort ();
  return 0;
}
