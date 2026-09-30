/* Equiv-rewrite of upstream libgomp.c/collapse-2.c.
 * "parallel for num_threads(8) collapse(3) schedule(static,9) reduction(+:l)
 * firstprivate(f)" lowered to GOMP ABI (collapse linearized, static start). */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

/* i in [-2,4), j in [-5,-2), k in [13,17) => 6*3*4 = 72 iterations.
 * Linear index = (i+2)*12 + (j+5)*4 + (k-13). */
static void
body (void *data)
{
  int *lp = data;
  int myl = 0;
  int f = 0;			/* firstprivate(f) */
  long istart, iend, idx;

  if (GOMP_loop_static_start (0, 72, 1, 9, &istart, &iend))
    {
      do
	{
	  for (idx = istart; idx < iend; idx++)
	    {
	      int i = idx / 12 - 2;
	      int j = (idx % 12) / 4 - 5;
	      int k = (idx % 4) + 13;
	      if (omp_get_num_threads () == 8
		  && idx != (omp_get_thread_num () * 9 + f++))
		myl++;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  GOMP_atomic_start ();
  *lp += myl;
  GOMP_atomic_end ();
}

int
main (void)
{
  int l = 0;

  GOMP_parallel (body, &l, 8, 0);

  if (l)
    abort ();
  return 0;
}
