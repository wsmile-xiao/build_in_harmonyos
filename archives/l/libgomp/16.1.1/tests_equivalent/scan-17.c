/* Equiv-rewrite of upstream libgomp.c/scan-17.c.  (simd variant: #pragma omp ... simd / simdlen / if(simd:0) are vectorization hints or serialization with no effect on the final array values; runtime-identical to scan-7.c
 * foo(): reduction(inscan, *:r) + scan exclusive(r) -> parallel exclusive
 *   product.  bar(): reduction(inscan, max:s) + scan exclusive(s) -> parallel
 *   exclusive running max.
 * Same GOMP two-phase scan as scan-3.c but with the exclusive ordering
 * (b[i] is written before updating the local accumulator).
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

extern void abort (void);

#define N 1024
float r = 1.0f, a[N], b[N];

static float *partial;
static float *offset;

struct scan_data {
  float *a;
  float *b;
  float result;
};

static void
product_body (void *p)
{
  struct scan_data *d = (struct scan_data *) p;
  int tid = omp_get_thread_num ();
  int nthr = omp_get_num_threads ();
  long i, istart, iend;
  long my_start = 0, my_end = 0;
  int have = 0;
  float local = 1.0f;

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      have = 1;
      my_start = istart;
      my_end = iend;
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      d->b[i] = local;             /* exclusive */
	      local *= d->a[i];
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  partial[tid] = local;

  GOMP_barrier ();

  if (tid == 0)
    {
      int t;
      float off = 1.0f;
      for (t = 0; t < nthr; t++)
	{
	  offset[t] = off;
	  off *= partial[t];
	}
      d->result = off;
    }

  GOMP_barrier ();

  if (have)
    {
      float off = offset[tid];
      for (i = my_start; i < my_end; i++)
	d->b[i] *= off;
    }

  GOMP_loop_end ();
}

static void
max_body (void *p)
{
  struct scan_data *d = (struct scan_data *) p;
  int tid = omp_get_thread_num ();
  int nthr = omp_get_num_threads ();
  long i, istart, iend;
  long my_start = 0, my_end = 0;
  int have = 0;
  float local = -__builtin_inff ();

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      have = 1;
      my_start = istart;
      my_end = iend;
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      d->b[i] = local;             /* exclusive */
	      local = local > d->a[i] ? local : d->a[i];
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  partial[tid] = local;

  GOMP_barrier ();

  if (tid == 0)
    {
      int t;
      float off = -__builtin_inff ();
      for (t = 0; t < nthr; t++)
	{
	  offset[t] = off;
	  off = off > partial[t] ? off : partial[t];
	}
      d->result = off;
    }

  GOMP_barrier ();

  if (have)
    {
      float off = offset[tid];
      for (i = my_start; i < my_end; i++)
	d->b[i] = d->b[i] > off ? d->b[i] : off;
    }

  GOMP_loop_end ();
}

static float
bar (void)
{
  struct scan_data d = { a, b, 0.0f };
  GOMP_parallel (max_body, &d, 0, 0);
  return d.result;
}

int
main (void)
{
  float s = 1.0f;
  for (int i = 0; i < 1024; ++i)
    {
      if (i < 80)
	a[i] = (i & 1) ? 0.25f : 0.5f;
      else if (i < 200)
	a[i] = (i % 3) == 0 ? 2.0f : (i % 3) == 1 ? 4.0f : 1.0f;
      else if (i < 280)
	a[i] = (i & 1) ? 0.25f : 0.5f;
      else if (i < 380)
	a[i] = (i % 3) == 0 ? 2.0f : (i % 3) == 1 ? 4.0f : 1.0f;
      else
	switch (i % 6)
	  {
	  case 0: a[i] = 0.25f; break;
	  case 1: a[i] = 2.0f; break;
	  case 2: a[i] = -1.0f; break;
	  case 3: a[i] = -4.0f; break;
	  case 4: a[i] = 0.5f; break;
	  case 5: a[i] = 1.0f; break;
	  default: a[i] = 0.0f; break;
	  }
      b[i] = -19.0f;
      asm ("" : "+g" (i));
    }

  partial = (float *) malloc ((size_t) omp_get_max_threads () * sizeof (float));
  offset  = (float *) malloc ((size_t) omp_get_max_threads () * sizeof (float));

  {
    struct scan_data d = { a, b, 0.0f };
    GOMP_parallel (product_body, &d, 0, 0);
    r = d.result;
  }
  if (r * 16384.0f != 0.125f)
    abort ();
  float m = -175.25f;
  for (int i = 0; i < 1024; ++i)
    {
      if (b[i] != s)
	abort ();
      else
	b[i] = -231.75f;
      s *= a[i];
      a[i] = m - ((i % 3) == 1 ? 2.0f : (i % 3) == 2 ? 4.0f : 0.0f);
      m += 0.75f;
    }
  if (bar () != 592.0f)
    abort ();
  s = -__builtin_inff ();
  for (int i = 0; i < 1024; ++i)
    {
      if (b[i] != s)
	abort ();
      if (s < a[i])
	s = a[i];
    }

  free (partial);
  free (offset);
  return 0;
}
