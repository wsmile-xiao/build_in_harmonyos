/* Equivalent rewrite: taskgroup task_reduction(*: sections) -> GOMP_taskgroup + atomic multiply.
 * For integer multiplication the reduction (private copy=identity, then combine) is identical to
 * atomically multiplying each factor into the shared element, since the initial value is 1. */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>
#include <string.h>

#define NR 14

struct red_ptrs
{
  int *p[NR];
};

static const int bar_factors[NR] = { 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25 };
static const int t2_factors[NR]  = {  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15 };

static void
red_apply (struct red_ptrs *d, const int *fac)
{
  int i;
  for (i = 0; i < NR; i++)
    {
      GOMP_atomic_start ();
      *d->p[i] *= fac[i];
      GOMP_atomic_end ();
    }
}

static void
bar_body (void *vp)
{
  red_apply ((struct red_ptrs *) vp, bar_factors);
}

static void
t2_body (void *vp)
{
  red_apply ((struct red_ptrs *) vp, t2_factors);
}

static void
check (int *a, int *b, int *c, int *d0, int *e0, int *f0, int *g0)
{
  if (a[0] != 24 || a[1] != 39 || b[3] != 56 || b[4] != 75)
    abort ();
  if (c[2] != 96 || c[3] != 119 || d0[0] != 144 || d0[1] != 171)
    abort ();
  if (e0[1] != 200 || e0[2] != 231 || f0[0] != 264 || f0[1] != 299)
    abort ();
  if (g0[1] != 336 || g0[2] != 375)
    abort ();
}

static void
foo (int n, int *d, int *e, int f[1][2], int g[1][4])
{
  int a[2], b[5], c[4];
  int i;
  struct red_ptrs p1, p2;

  for (i = 0; i < n; i++)
    {
      a[i] = 1;
      b[i + 3] = 1;
      c[i + n] = 1;
      d[i] = 1;
      e[i + 1] = 1;
      f[0][i] = 1;
      g[0][i + 1] = 1;
    }

  {
    int *base[NR] = {
      &a[0], &a[1], &b[3], &b[4], &c[n], &c[n + 1],
      &d[0], &d[1], &e[1], &e[2],
      &f[0][0], &f[0][1], &g[0][1], &g[0][2]
    };
    for (i = 0; i < NR; i++)
      {
	p1.p[i] = base[i];
	p2.p[i] = base[i];
      }
  }

  GOMP_taskgroup_start ();
  GOMP_task (bar_body, &p1, NULL, sizeof (p1), __alignof__ (struct red_ptrs),
	     1, 0, NULL, 0, NULL);
  GOMP_task (t2_body, &p2, NULL, sizeof (p2), __alignof__ (struct red_ptrs),
	     1, 0, NULL, 0, NULL);
  n = 0;
  GOMP_taskgroup_end ();

  check (a, b, c, d, e, f[0], g[0]);
}

int
main ()
{
  int d[2], e[4], f[1][2], g[1][4];

  foo (2, d, e, f, g);

  return 0;
}
