/* Equiv-rewrite of upstream loop-9.c.
 * `#pragma omp parallel for collapse(2) reduction(+:sum) lastprivate(p,q)`:
 * the 8x8 iteration space is linearized and distributed via GOMP_loop_static,
 * sum is reduced via per-thread copies, and lastprivate(p,q) reproduces the
 * sequential exit values &buf[8] / buf2+8.
 */
#include <stdlib.h>
#include <omp.h>
#include "libgomp_g.h"

extern void abort (void);

char buf[8] = "01234567";
char buf2[8] = "23456789";

struct data { int *sum_priv; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int tid = omp_get_thread_num ();
  long t, istart, iend;
  int local = 0;

  if (GOMP_loop_static_start (0, 64, 1, 0, &istart, &iend))
    {
      do
	{
	  for (t = istart; t < iend; t++)
	    {
	      long pi = t / 8;
	      long qi = t % 8;
	      local += (buf[pi] - '0') + (buf2[qi] - '0');
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  d->sum_priv[tid] = local;
}

int
main (void)
{
  char *p, *q;
  int sum = 0;
  int nt = omp_get_max_threads ();
  int *sp = (int *) calloc ((size_t) nt, sizeof (int));
  struct data d = { sp };
  int t;

  if (nt < 1)
    nt = 1;

  GOMP_parallel (body, &d, 0, 0);

  for (t = 0; t < nt; t++)
    sum += sp[t];
  free (sp);

  p = &buf[8];   /* lastprivate(p) */
  q = buf2 + 8;  /* lastprivate(q) */

  if (p != &buf[8] || q != buf2 + 8 || sum != 576)
    abort ();
  return 0;
}
