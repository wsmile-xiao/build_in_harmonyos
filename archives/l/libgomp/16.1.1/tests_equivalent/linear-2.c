/* Equiv-rewrite of upstream linear-2.c.
 * `parallel for simd linear(i:step)` — simd is only a vectorization hint, so
 * the lowering is identical to linear-1.c (GOMP_parallel + GOMP_loop_static).
 */
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "b2g2_common.h"

int a[256];

struct ld { long base; long linstep; long n; long val0; long valstep; };

static void
lin_body (void *p)
{
  struct ld *d = (struct ld *) p;
  long istart, iend, iter;
  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (iter = istart; iter < iend; iter++)
	    a[d->base + d->linstep * iter] = (int) (d->val0 + d->valstep * iter);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
lin_run (long base, long linstep, long n, long val0, long valstep)
{
  struct ld d = { base, linstep, n, val0, valstep };
  GOMP_parallel (lin_body, &d, 0, 0);
}

int           f1 (int i)                        { lin_run (i, 4, 48, 16, 1); return i + 4 * 48; }
short int     f2 (short int i, char k)          { lin_run (i, k + 1, 48, 16, 1); return i + (k + 1) * 48; }
long long int f3 (long long int i, long long k) { lin_run (i, k, 48, 16, 1); return i + k * 48; }
int           f4 (int i)                        { lin_run (i, 4, 48, 16, 1); return i + 4 * 48; }
short int     f5 (short int i, char k)          { lin_run (i, k + 1, 48, 16, 1); return i + (k + 1) * 48; }
long long int f6 (long long int i, long long k) { lin_run (i, k, 48, 16, 1); return i + k * 48; }
int           f7 (int i)                        { lin_run (i, 4, 48, 16, 1); return i + 4 * 48; }
short int     f8 (short int i, char k)          { lin_run (i, k + 1, 48, 16, 1); return i + (k + 1) * 48; }
long long int f9 (long long int i, long long k) { lin_run (i, k, 48, 16, 1); return i + k * 48; }

int           f10 (int i, long step)                        { long n = (112 - 16 + step - 1) / step; lin_run (i, 4, n, 16, step / 2); return i + 4 * n; }
short int     f11 (short int i, char k, char step)          { long n = (112 - 16 + step - 1) / step; lin_run (i, k + 1, n, 16, step / 2); return i + (k + 1) * n; }
long long int f12 (long long int i, long long k, int step)  { long n = (112 - 16 + step - 1) / step; lin_run (i, k, n, 16, step / 2); return i + k * n; }
int           f13 (int i, long long int step)               { long n = (112 - 16 + step - 1) / step; lin_run (i, 4, n, 16, step / 2); return i + 4 * n; }
short int     f14 (short int i, char k, int step)           { long n = (112 - 16 + step - 1) / step; lin_run (i, k + 1, n, 16, step / 2); return i + (k + 1) * n; }
long long int f15 (long long int i, long long k, long step) { long n = (112 - 16 + step - 1) / step; lin_run (i, k, n, 16, step / 2); return i + k * n; }
int           f16 (int i, long long int step)               { long n = (112 - 16 + step - 1) / step; lin_run (i, 4, n, 16, step / 2); return i + 4 * n; }
short int     f17 (short int i, char k, int step)           { long n = (112 - 16 + step - 1) / step; lin_run (i, k + 1, n, 16, step / 2); return i + (k + 1) * n; }
long long int f18 (long long int i, long long k, long step) { long n = (112 - 16 + step - 1) / step; lin_run (i, k, n, 16, step / 2); return i + k * n; }

#define TEST(x) \
  do { \
    if ((x) != 8 + 48 * 4) abort (); \
    for (int i = 0; i < 256; i++) \
      if (a[i] != (((i & 3) == 0 && i >= 8 && i < 8 + 48 * 4) \
		   ? ((i - 8) / 4) + 16 : 0)) \
	abort (); \
    memset (a, 0, sizeof (a)); \
  } while (0)

int
main ()
{
  TEST (f1 (8));
  TEST (f2 (8, 3));
  TEST (f3 (8LL, 4LL));
  TEST (f4 (8));
  TEST (f5 (8, 3));
  TEST (f6 (8LL, 4LL));
  TEST (f7 (8));
  TEST (f8 (8, 3));
  TEST (f9 (8LL, 4LL));
  TEST (f10 (8, 2));
  TEST (f11 (8, 3, 2));
  TEST (f12 (8LL, 4LL, 2));
  TEST (f13 (8, 2));
  TEST (f14 (8, 3, 2));
  TEST (f15 (8LL, 4LL, 2));
  TEST (f16 (8, 2));
  TEST (f17 (8, 3, 2));
  TEST (f18 (8LL, 4LL, 2));
  return 0;
}
