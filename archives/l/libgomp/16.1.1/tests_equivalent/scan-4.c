/* Equiv-rewrite of upstream libgomp.c/scan-4.c.
 * reduction(inscan, +:r, r2, r3) + scan inclusive over int/unsigned short/
 * unsigned char.  The three accumulators receive identical inputs a[i], and
 * modular (wrapping) arithmetic is associative, so b2[i]==(unsigned short)b[i]
 * and b3[i]==(unsigned char)b[i].  We therefore run one int inclusive prefix
 * scan (same as scan-1.c) and derive the narrow types from it.
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

extern void abort (void);

#define N 1024
int r, a[N], b[N];
unsigned short r2, b2[N];
unsigned char r3, b3[N];

static int *partial;
static int *offset;

struct scan_data {
  int *a;
  int *b;
  unsigned short *b2;
  unsigned char *b3;
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
	{
	  d->b[i] += off;
	  d->b2[i] = (unsigned short) d->b[i];
	  d->b3[i] = (unsigned char) d->b[i];
	}
    }

  GOMP_loop_end ();
}

static int
bar (unsigned short *s2p, unsigned char *s3p)
{
  struct scan_data d = { a, b, b2, b3, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  *s2p = (unsigned short) d.result;
  *s3p = (unsigned char) d.result;
  return d.result;
}

static int
qux (unsigned short *s2p, unsigned char *s3p)
{
  struct scan_data d = { a, b, b2, b3, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  *s2p = (unsigned short) d.result;
  *s3p = (unsigned char) d.result;
  return d.result;
}

int
main (void)
{
  int s = 0;
  unsigned short s2;
  unsigned char s3;
  for (int i = 0; i < 1024; ++i)
    {
      a[i] = i;
      b[i] = -1;
      b2[i] = -1;
      b3[i] = -1;
      asm ("" : "+g" (i));
    }

  partial = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));
  offset  = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));

  {
    struct scan_data d = { a, b, b2, b3, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  r2 = (unsigned short) r;
  r3 = (unsigned char) r;
  if (r != 1024 * 1023 / 2
      || r2 != (unsigned short) r
      || r3 != (unsigned char) r)
    abort ();
  for (int i = 0; i < 1024; ++i)
    {
      s += i;
      if (b[i] != s
	  || b2[i] != (unsigned short) s
	  || b3[i] != (unsigned char) s)
	abort ();
      else
	{
	  b[i] = 25;
	  b2[i] = 24;
	  b3[i] = 26;
	}
    }
  if (bar (&s2, &s3) != 1024 * 1023)
    abort ();
  if (s2 != (unsigned short) (1024 * 1023)
      || s3 != (unsigned char) (1024 * 1023))
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += 2 * i;
      if (b[i] != s
	  || b2[i] != (unsigned short) s
	  || b3[i] != (unsigned char) s)
	abort ();
      else
	{
	  b[i] = -1;
	  b2[i] = -1;
	  b3[i] = -1;
	}
    }
  r = 0;
  r2 = 0;
  r3 = 0;
  {
    struct scan_data d = { a, b, b2, b3, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  r2 = (unsigned short) r;
  r3 = (unsigned char) r;
  if (r != 1024 * 1023 / 2
      || r2 != (unsigned short) r
      || r3 != (unsigned char) r)
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += i;
      if (b[i] != s
	  || b2[i] != (unsigned short) s
	  || b3[i] != (unsigned char) s)
	abort ();
      else
	{
	  b[i] = 25;
	  b2[i] = 24;
	  b3[i] = 26;
	}
    }
  s2 = 0;
  s3 = 0;
  if (qux (&s2, &s3) != 1024 * 1023)
    abort ();
  if (s2 != (unsigned short) (1024 * 1023)
      || s3 != (unsigned char) (1024 * 1023))
    abort ();
  s = 0;
  for (int i = 0; i < 1024; ++i)
    {
      s += 2 * i;
      if (b[i] != s
	  || b2[i] != (unsigned short) s
	  || b3[i] != (unsigned char) s)
	abort ();
    }

  free (partial);
  free (offset);
  return 0;
}
