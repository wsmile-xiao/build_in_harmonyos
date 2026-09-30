/* Equiv-rewrite of upstream loop-4.c.
 * `#pragma omp parallel num_threads(4) reduction(+:e)` with two
 * `#pragma omp for schedule(dynamic,1)` worksharing loops -> GOMP_parallel +
 * GOMP_loop_dynamic_start + per-thread reduction copies.
 */
#include <omp.h>
#include "libgomp_g.h"

extern void abort (void);

struct data { int e[4]; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int tid = omp_get_thread_num ();
  long i, istart, iend;

  /* for (i = LONG_MAX-30001; i <= LONG_MAX-10001; i += 10000)  [dynamic,1] */
  if (GOMP_loop_dynamic_start (__LONG_MAX__ - 30001, __LONG_MAX__ - 10000,
			       10000, 1, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i += 10000)
	    if (i != __LONG_MAX__ - 30001
		&& i != __LONG_MAX__ - 20001
		&& i != __LONG_MAX__ - 10001)
	      d->e[tid] = 1;
	}
      while (GOMP_loop_dynamic_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* for (i = -LONG_MAX+30000; i >= -LONG_MAX+10000; i -= 10000)  [dynamic,1] */
  if (GOMP_loop_dynamic_start (-__LONG_MAX__ + 30000, -__LONG_MAX__ + 0,
			       -10000, 1, &istart, &iend))
    {
      do
	{
	  for (i = istart; i > iend; i -= 10000)
	    if (i != -__LONG_MAX__ + 30000
		&& i != -__LONG_MAX__ + 20000
		&& i != -__LONG_MAX__ + 10000)
	      d->e[tid] = 1;
	}
      while (GOMP_loop_dynamic_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int e = 0;
  struct data d = { { 0, 0, 0, 0 } };
  int t;

  GOMP_parallel (body, &d, 4, 0);

  for (t = 0; t < 4; t++)
    e += d.e[t];

  if (e)
    abort ();
  return 0;
}
