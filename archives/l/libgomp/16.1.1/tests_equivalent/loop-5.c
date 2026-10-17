/* Equiv-rewrite of upstream loop-5.c.
 * `#pragma omp parallel for [schedule(...)]` over pointer loops -> GOMP
 * worksharing over the (integer) element indices.  Each iteration writes a
 * distinct element so no further synchronization is needed.  The element
 * type (short vs int) is immaterial here; an int buffer is used throughout.
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>
#include "b2g2_common.h"

struct c { int *buf; int kind; };

static void
put (void *ctx, long idx)
{
  struct c *d = (struct c *) ctx;
  long off;
  int val;

  switch (d->kind)
    {
    case 0: off = 0;  val = 5;  break;
    case 1: off = -2; val = 6;  break;
    case 2: off = 2;  val = 7;  break;
    default: off = 2; val = -7; break;
    }
  d->buf[idx + off] = val;
}

#define PLOOP(buf, kind, sched, chunk, start, end, incr)		\
  do {									\
    struct c c_ = { (buf), (kind) };					\
    struct b2g2_ws w_ = { &c_, put, (sched), (start), (end), (incr), (chunk) }; \
    b2g2_parallel_for (&w_, 0);					\
  } while (0)

static void
run (int sched, long chunk)
{
  int buf[64];
  int i;

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 0, sched, chunk, 10, 54, 1);
  for (i = 0; i < 64; i++)
    if (buf[i] != 5 * (i >= 10 && i < 54))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 1, sched, chunk, 3, 64, 2);
  for (i = 0; i < 64; i++)
    if (buf[i] != 6 * ((i & 1) && i <= 61))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 2, sched, chunk, 16, 51, 4);
  for (i = 0; i < 64; i++)
    if (buf[i] != 7 * ((i & 3) == 2 && i >= 18 && i < 53))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 3, sched, chunk, 16, 41, 4);
  for (i = 0; i < 64; i++)
    if (buf[i] != -7 * ((i & 3) == 2 && i >= 18 && i <= 42))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 0, sched, chunk, 53, 9, -1);
  for (i = 0; i < 64; i++)
    if (buf[i] != 5 * (i >= 10 && i < 54))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 1, sched, chunk, 63, 1, -2);
  for (i = 0; i < 64; i++)
    if (buf[i] != 6 * ((i & 1) && i <= 61))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 2, sched, chunk, 48, 12, -4);
  for (i = 0; i < 64; i++)
    if (buf[i] != 7 * ((i & 3) == 2 && i >= 18 && i < 53))
      abort ();

  memset (buf, 0, sizeof (buf));
  PLOOP (buf, 3, sched, chunk, 40, 12, -4);
  for (i = 0; i < 64; i++)
    if (buf[i] != -7 * ((i & 3) == 2 && i >= 18 && i <= 42))
      abort ();
}

int
main (void)
{
  run (0, 0);           /* default (static) */
  run (0, 3);           /* static,3 */
  run (1, 3);           /* dynamic,3 */
  omp_set_schedule (omp_sched_static, 0);
  run (3, 0);           /* runtime */
  omp_set_schedule (omp_sched_static, 3);
  run (3, 0);
  omp_set_schedule (omp_sched_dynamic, 5);
  run (3, 0);
  omp_set_schedule (omp_sched_guided, 2);
  run (3, 0);
  return 0;
}
