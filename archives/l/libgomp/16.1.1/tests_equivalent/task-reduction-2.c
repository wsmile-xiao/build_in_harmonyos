/* Equivalent rewrite: "parallel ... reduction(task, *: ...)" -> GOMP_parallel + atomic multiply.
 * Integer multiplication reduction is identical to atomically multiplying each factor. */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>
#include <string.h>

#define NR 14

struct red_ptrs
{
  int *p[NR];
};

struct par_ctx
{
  struct red_ptrs p1;
  struct red_ptrs p2;
  int n;   /* firstprivate */
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
par_fn (void *vp)
{
  struct par_ctx *c = (struct par_ctx *) vp;
  int n = c->n;  /* firstprivate */

  if (omp_get_thread_num () == 0)
    {
      GOMP_task (bar_body, &c->p1, NULL, sizeof (struct red_ptrs),
		 __alignof__ (struct red_ptrs), 1, 0, NULL, 0, NULL);
      GOMP_task (t2_body, &c->p2, NULL, sizeof (struct red_ptrs),
		 __alignof__ (struct red_ptrs), 1, 0, NULL, 0, NULL);
    }
  n = 0;
}

static void
baz (int n, int *d, int *e, int f[1][2], int g[1][4])
{
  int a[2], b[5], c[4];
  int i;
  struct par_ctx pc;

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
	pc.p1.p[i] = base[i];
	pc.p2.p[i] = base[i];
      }
  }
  pc.n = n;

  GOMP_parallel (par_fn, &pc, 2, 0);

  if (a[0] != 24 || a[1] != 39 || b[3] != 56 || b[4] != 75)
    abort ();
  if (c[2] != 96 || c[3] != 119 || d[0] != 144 || d[1] != 171)
    abort ();
  if (e[1] != 200 || e[2] != 231 || f[0][0] != 264 || f[0][1] != 299)
    abort ();
  if (g[0][1] != 336 || g[0][2] != 375)
    abort ();
}

int
main ()
{
  int d[2], e[4], f[1][2], g[1][4];

  baz (2, d, e, f, g);

  return 0;
}
