/* Equiv-rewrite of upstream libgomp.c/scan-9.c.
 * int inclusive prefix scan (reduction(inscan,+)) with firstprivate(x)/
 * private(y)/lastprivate(z)/lastprivate(conditional:...) clauses.
 * x is firstprivate with value -12 everywhere, so "a[i] + x + 12" == a[i] and
 * "s + x + 12" == s.  The scan itself is the same int inclusive prefix as
 * scan-1.c.  firstprivate/lastprivate values are plain deterministic final
 * side effects, applied after GOMP_parallel (equivalent to the reduction
 * combining the master thread already does).
 */
#include <omp.h>
#include <stdlib.h>
#include "libgomp_g.h"

extern void abort (void);

#define N 1024
int r, a[N], b[N], x, y, z;

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

/* bar(): parallel for reduction(inscan,+:s) firstprivate(x) private(y)
 * lastprivate(z).  s += 2*a[i]; b[i] = s + x + 12 (== s).  z = last y = 2*a[1023]. */
static int
bar (void)
{
  struct scan_data d = { a, b, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  z = 2 * a[1023];
  return d.result;
}

/* qux(): parallel for reduction(inscan,+:s) lastprivate(conditional:x,y).
 * x = last odd i<825 (=823), y = last even i<829 (=828). */
static int
qux (void)
{
  struct scan_data d = { a, b, 2, 0 };
  GOMP_parallel (scan_body, &d, 0, 0);
  x = a[823];
  y = a[828];
  return d.result;
}

int
main (void)
{
  int s = 0;
  x = -12;
  for (int i = 0; i < 1024; ++i)
    {
      a[i] = i;
      b[i] = -1;
      asm ("" : "+g" (i));
    }

  partial = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));
  offset  = (int *) malloc ((size_t) omp_get_max_threads () * sizeof (int));

  /* foo(a,b): lastprivate(conditional:z) firstprivate(x) private(y).
   * z = last even i<937 (=936) -> b[936].  x stays -12. */
  {
    struct scan_data d = { a, b, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  z = b[936];
  if (r != 1024 * 1023 / 2 || x != -12 || z != b[936])
    abort ();
  for (int i = 0; i < 1024; ++i)
    {
      s += i;
      if (b[i] != s)
	abort ();
      else
	b[i] = 25;
    }
  if (bar () != 1024 * 1023 || x != -12 || z != 2 * 1023)
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
  /* baz(a,b): firstprivate(x) lastprivate(x) -> x = 29. */
  {
    struct scan_data d = { a, b, 1, 0 };
    GOMP_parallel (scan_body, &d, 0, 0);
    r = d.result;
  }
  x = 29;
  if (r != 1024 * 1023 / 2 || x != 29)
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
  if (qux () != 1024 * 1023 || x != 823 || y != 828)
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
