/* static-chunk-size-one.c — 完全等价改写
 * parallel for num_threads(3) reduction(+:a) schedule(static,1) → GOMP ABI。
 */
#include <stdlib.h>
#include <stdbool.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

struct d
{
  int *partials;
};

static void
fn (void *arg)
{
  struct d *d = (struct d *) arg;
  long istart, iend;
  int i;
  int local = 0;
  if (GOMP_loop_static_start (0, 10, 1, 1, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    local += i;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->partials[omp_get_thread_num ()] = local;
}

int
bar (void)
{
  int a = 0, i;
  int maxn = omp_get_max_threads ();
  int *partials = (int *) calloc (maxn, sizeof (int));
  struct d d = { partials };

  GOMP_parallel (fn, &d, 3, 0);

  for (i = 0; i < maxn; i++)
    a += partials[i];
  free (partials);
  return a;
}

int
main (void)
{
  int res;
  res = bar ();
  if (res != 45)
    abort ();
  return 0;
}
