/* PR libgomp/122281 - equiv rewrite. target + parallel for simd + atomic cnt
 * (host-only) -> GOMP_parallel + GOMP_loop_static + GOMP_atomic; cnt == n (all nonzero).
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

struct ctx { int *A; int n; int *cnt; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, x->n, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    if (x->A[i] != 0)
	      {
		GOMP_atomic_start ();
		(*x->cnt)++;
		GOMP_atomic_end ();
	      }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static int
f (int *A, int n, int dev)
{
  (void) dev;
  int cnt = 0;
  struct ctx x = { A, n, &cnt };
  GOMP_parallel (body, &x, 0, 0);
  return cnt;
}

int
main (void)
{
  int n = 10;
  int A[10] = { 11, 22, 33, 44, 55, 66, 77, 88, 99, 110 };
  for (int dev = omp_initial_device; dev <= omp_get_num_devices (); dev++)
    if (f (A, n, dev) != 10)
      abort ();
  return 0;
}
