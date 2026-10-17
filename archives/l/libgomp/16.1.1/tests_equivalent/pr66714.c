/* Equiv-rewrite of upstream pr66714.c (dg-do compile with -g; a minimized GCC
 * ICE for target + parallel-for over a VLA). On host the target runs on the
 * initial device, so we outline the parallel-for and make it runnable.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

struct d { int x; double *b; };

static void
body (void *p)
{
  struct d *d = (struct d *) p;
  long istart, iend;
  if (GOMP_loop_static_start (0, d->x, 1, 0, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  d->b[i] += 1;
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

void
fn3 (int x)
{
  double b[3 * x];
  for (int i = 0; i < 3 * x; i++)
    b[i] = 0;
  struct d dd = { x, b };
  GOMP_parallel (body, &dd, 0, 0);
  for (int i = 0; i < x; i++)
    if (b[i] != 1.0)
      __builtin_abort ();
}

int
main (void)
{
  fn3 (100);
  return 0;
}
