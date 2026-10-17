/* Equiv-rewrite of upstream libgomp.c/ordered-5.c.
 * "parallel for simd ordered" + "ordered threads simd" lowered to GOMP ABI
 * (host-only: simd is a no-op hint; GOMP_loop_ordered_static_start +
 * GOMP_ordered_start/end). */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_ordered_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_ordered_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_ordered_start (void);
extern void GOMP_ordered_end (void);

static int a[1024], b = -1;

static void
body (void *d)
{
  (void) d;
  long i, is, ie;

  if (GOMP_loop_ordered_static_start (0, 1024, 1, 1, &is, &ie))
    {
      do
	{
	  for (i = is; i < ie; i++)
	    {
	      a[i] = i;
	      GOMP_ordered_start ();
	      {
		if (b + 1 != i)
		  abort ();
		b = i;
	      }
	      GOMP_ordered_end ();
	      a[i] += 3;
	    }
	}
      while (GOMP_loop_ordered_static_next (&is, &ie));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int i;

  GOMP_parallel (body, 0, 0, 0);

  if (b != 1023)
    abort ();
  for (i = 0; i < 1024; i++)
    if (a[i] != i + 3)
      abort ();
  return 0;
}
