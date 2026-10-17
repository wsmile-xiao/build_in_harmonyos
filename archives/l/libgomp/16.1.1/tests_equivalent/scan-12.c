/* Equiv-rewrite of upstream libgomp.c/scan-12.c.  (simd variant: #pragma omp ... simd / simdlen / if(simd:0) are vectorization hints or serialization with no effect on the final array values; runtime-identical to scan-2.c
 * Identical to scan-1.c: `#pragma omp declare reduction(foo: int: omp_out +=
 * omp_in) initializer(omp_priv = 0)` defines `+`, so `reduction(inscan, foo:r)`
 * is just an int inclusive prefix sum.  Same GOMP outline as scan-1.c.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

extern void abort (void);

#define N 1024
int r, a[N], b[N];

static int *partial;
static int *offset;

struct scan_data {
  int *a;
  int *b;
  int mul;
  int result;
};

static void
scan_body (void *p)
{
  struct scan_data *d = (struct scan_data *) p;
  int tid = omp_get_thread_num ();
  int nthr = omp_get_num_threads ();
  long i, istart, iend;
  long my_start = 0, my_end = 0;
  int have = 0, local = 0;

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      have = 1;
      my_start = istart;
      my_end = iend;
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      local += d->mul * d->a[i];
	      d->b[i] = local;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  partial[tid] = local;

  GOMP_barrier ();

  if (tid == 0)
    {
      int t, off = 0;
      for (t = 0; t < nthr; t++)
	{
	  offset[t] = off;
	  off += partial[t];
	}
      d->result = off;
    }

  GOMP_barrier ();

  if (have)
    {
      int off = offset[tid];
      for (i = my_start; i < my_end; i++)
	d->b[i] += off;
    }

  GOMP_loop_end ();
}

static int
bar (void)
{
  struct scan_data d = { a, b, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  return d.result;
}

static int
qux (void)
{
  struct scan_data d = { a, b, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  return d.result;
}

int
main (void)
{
  int s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      a[i] = i;
      b[i] = -1;
      asm ("" : "+g" (i));
    }

  partial = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));
  offset  = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));

  {
    struct scan_data d = { a, b, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  if (r != 1024 * 1023 / 2)
    abort ();
  for (int i = 0; i < 1024; ++i)
    {
      s += i;
      if (b[i] != s)
	abort ();
      else
	b[i] = 25;
    }
  if (bar () != 1024 * 1023)
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += 2 * i;
      if (b[i] != s)
	abort ();
      else
	b[i] = -1;
    }
  r = 0;
  {
    struct scan_data d = { a, b, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  if (r != 1024 * 1023 / 2)
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += i;
      if (b[i] != s)
	abort ();
      else
	b[i] = -25;
    }
  if (qux () != 1024 * 1023)
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += 2 * i;
      if (b[i] != s)
	abort ();
    }

  free (partial);
  free (offset);
  return 0;
}
