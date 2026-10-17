/* Common helpers for the b2g2 GOMP-ABI equivalence rewrites.
 * Included by each rewritten test.  Provides thin drivers over the GOMP
 * worksharing entry points (declared in libgomp_g.h, which is found via -I$SRC).
 */
#ifndef B2G2_COMMON_H
#define B2G2_COMMON_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "libgomp_g.h"

/* ---- signed (long) worksharing loop, inside an active parallel region ---- */

typedef void (*b2g2_iter_fn) (void *ctx, long idx);

struct b2g2_ws
{
  void *ctx;
  b2g2_iter_fn iter;
  int sched;            /* 0 static, 1 dynamic, 2 guided, 3 runtime */
  long start, end;      /* half-open [start, end) in the direction of incr */
  long incr;            /* signed stride (negative => descending) */
  long chunk;           /* chunk size (ignored by runtime schedule) */
};

static inline void
b2g2_ws (struct b2g2_ws *d, int nowait)
{
  long istart, iend, idx;
  bool have = false;

  switch (d->sched)
    {
    case 0:
      have = GOMP_loop_static_start (d->start, d->end, d->incr, d->chunk,
				     &istart, &iend);
      break;
    case 1:
      have = GOMP_loop_dynamic_start (d->start, d->end, d->incr, d->chunk,
				      &istart, &iend);
      break;
    case 2:
      have = GOMP_loop_guided_start (d->start, d->end, d->incr, d->chunk,
				     &istart, &iend);
      break;
    default:
      have = GOMP_loop_runtime_start (d->start, d->end, d->incr,
				      &istart, &iend);
      break;
    }

  if (have)
    {
      do
	{
	  if (d->incr > 0)
	    for (idx = istart; idx < iend; idx += d->incr)
	      d->iter (d->ctx, idx);
	  else
	    for (idx = istart; idx > iend; idx += d->incr)
	      d->iter (d->ctx, idx);

	  switch (d->sched)
	    {
	    case 0: have = GOMP_loop_static_next (&istart, &iend); break;
	    case 1: have = GOMP_loop_dynamic_next (&istart, &iend); break;
	    case 2: have = GOMP_loop_guided_next (&istart, &iend); break;
	    default: have = GOMP_loop_runtime_next (&istart, &iend); break;
	    }
	}
      while (have);
    }

  if (nowait)
    GOMP_loop_end_nowait ();
  else
    GOMP_loop_end ();
}

/* ---- unsigned long long worksharing loop (ascending only) ---- */

typedef void (*b2g2_iter_ull_fn) (void *ctx, unsigned long long idx);

struct b2g2_ws_ull
{
  void *ctx;
  b2g2_iter_ull_fn iter;
  int sched;                      /* 0 static, 1 dynamic, 2 guided, 3 runtime */
  unsigned long long start, end;  /* half-open [start, end) ascending */
  unsigned long long incr;        /* positive stride */
  unsigned long long chunk;
};

static inline void
b2g2_ws_ull (struct b2g2_ws_ull *d, int nowait)
{
  unsigned long long istart, iend, idx;
  bool have = false;

  switch (d->sched)
    {
    case 0:
      have = GOMP_loop_ull_static_start (true, d->start, d->end, d->incr,
					 d->chunk, &istart, &iend);
      break;
    case 1:
      have = GOMP_loop_ull_dynamic_start (true, d->start, d->end, d->incr,
					  d->chunk, &istart, &iend);
      break;
    case 2:
      have = GOMP_loop_ull_guided_start (true, d->start, d->end, d->incr,
					 d->chunk, &istart, &iend);
      break;
    default:
      have = GOMP_loop_ull_runtime_start (true, d->start, d->end, d->incr,
					  &istart, &iend);
      break;
    }

  if (have)
    {
      do
	{
	  for (idx = istart; idx < iend; idx += d->incr)
	    d->iter (d->ctx, idx);

	  switch (d->sched)
	    {
	    case 0: have = GOMP_loop_ull_static_next (&istart, &iend); break;
	    case 1: have = GOMP_loop_ull_dynamic_next (&istart, &iend); break;
	    case 2: have = GOMP_loop_ull_guided_next (&istart, &iend); break;
	    default: have = GOMP_loop_ull_runtime_next (&istart, &iend); break;
	    }
	}
      while (have);
    }

  if (nowait)
    GOMP_loop_end_nowait ();
  else
    GOMP_loop_end ();
}

/* ---- combined parallel-for (single worksharing loop, signed indices) ---- */

struct b2g2_pf
{
  struct b2g2_ws ws;
};

static void
b2g2_pf_body (void *p)
{
  struct b2g2_pf *d = (struct b2g2_pf *) p;
  b2g2_ws (&d->ws, 0);
}

static inline void
b2g2_parallel_for (struct b2g2_ws *ws, unsigned nthreads)
{
  struct b2g2_pf d = { *ws };
  GOMP_parallel (b2g2_pf_body, &d, nthreads, 0);
}

#endif /* B2G2_COMMON_H */
