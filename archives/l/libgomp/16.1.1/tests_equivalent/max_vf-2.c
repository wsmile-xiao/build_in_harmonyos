/* max_vf-2.c — 完全等价改写 (dg-do link，host-only)
 * target teams distribute parallel for simd reduction(+:sum) → host parallel for + 手动归约。
 */
#include <stdlib.h>
#include <stdbool.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

struct fd
{
  float *a, *b;
  int n;
  float *partials;
};

static void
f_fn (void *arg)
{
  struct fd *d = (struct fd *) arg;
  long istart, iend;
  float sum = 0;
  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	{
	  int i;
	  for (i = istart; i < iend; i++)
	    sum += d->a[i] * d->b[i];
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->partials[omp_get_thread_num ()] = sum;
}

int
f (float *a, float *b, int n)
{
  float sum = 0;
  int maxn = omp_get_max_threads ();
  int i;
  float *partials = (float *) calloc (maxn, sizeof (float));
  struct fd d = { a, b, n, partials };
  GOMP_parallel (f_fn, &d, 0, 0);
  for (i = 0; i < maxn; i++)
    sum += partials[i];
  free (partials);
  return (int) sum;
}

int
main (void)
{
  return 0;
}
