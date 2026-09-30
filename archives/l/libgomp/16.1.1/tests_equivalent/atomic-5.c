/* Equiv-rewrite of upstream atomic-5.c: parallel for shared(d) + atomic. */
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern int GOMP_loop_static_start (long, long, long, long, long *, long *);
extern int GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static void
body (void *p)
{
  long double *d = (long double *) p;
  long istart, iend;
  int i;
  if (GOMP_loop_static_start (0, 10, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      GOMP_atomic_start (); *d += 1.0L; GOMP_atomic_end ();
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int __attribute__((noinline))
do_test (void)
{
  long double d = .0L;
  GOMP_parallel (body, &d, 0, 0);
  if (d != 10.0L)
    abort ();
  return 0;
}

int
main (void)
{
  do_test ();
  return 0;
}
