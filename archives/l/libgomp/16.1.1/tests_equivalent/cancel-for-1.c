/* Equiv-rewrite of upstream libgomp.c/cancel-for-1.c.
 * #pragma omp parallel num_threads(32) { #pragma omp for { #pragma omp cancel for } }
 * manually lowered to GOMP ABI.  Run with OMP_CANCELLATION=true. */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern _Bool GOMP_cancel (int, _Bool);

#define GOMP_CANCEL_PARALLEL 1
#define GOMP_CANCEL_LOOP 2

static void
body (void *data)
{
  (void) data;
  long i, istart, iend;

  if (GOMP_loop_static_start (0, 1000, 1, 1, &istart, &iend))
    {
      int cancelled = 0;
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      if (GOMP_cancel (GOMP_CANCEL_LOOP, 1))
		{
		  cancelled = 1;
		  break;
		}
	      if (omp_get_cancellation ())
		abort ();
	    }
	  if (cancelled)
	    break;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  GOMP_parallel (body, 0, 32, 0);
  return 0;
}
