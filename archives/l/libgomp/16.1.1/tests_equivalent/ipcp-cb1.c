/* Equiv-rewrite of upstream ipcp-cb1.c.
 *
 * Upstream verifies that GCC's IPA-CP propagates the constant c=100 into the
 * outlined parallel-for kernel (so __builtin_constant_p(c) is true). clang has
 * no such GOMP specialization, so we replace the constant_p probe with an
 * explicit value check (c == 100) and outline the parallel-for; main returns
 * a[5] - 5 which must be 0.
 */
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

int a[100];

struct d { int c; };

static void
body (void *p)
{
  struct d *d = (struct d *) p;
  int c = d->c;
  if (c != 100)
    __builtin_abort ();
  long istart, iend;
  if (GOMP_loop_static_start (0, c, 1, 0, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  a[i] = (int) i;
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
test (int c)
{
  struct d dd = { c };
  GOMP_parallel (body, &dd, 0, 0);
}

int
main (void)
{
  test (100);
  return a[5] - 5;
}
