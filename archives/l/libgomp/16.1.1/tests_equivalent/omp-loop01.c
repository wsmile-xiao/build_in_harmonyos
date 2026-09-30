/* Equivalent rewrite: 4 x "parallel ... for" with varied bounds -> GOMP_loop_static_start */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <omp.h>
#include "libgomp_g.h"

#define MAX 1000

enum loop_mode { UP_LT, UP_LE, DOWN_GT, DOWN_GE };

struct loop_ctx
{
  int *a;
  int *b;
  int N1, N2, step;
  enum loop_mode mode;
};

static void
loop_body (void *vp)
{
  struct loop_ctx *d = (struct loop_ctx *) vp;
  int i;
  long istart, iend;
  int start, end, incr;

  switch (d->mode)
    {
    case UP_LT:   start = d->N1;     end = d->N2;     incr = d->step;  break;
    case UP_LE:   start = d->N1;     end = d->N2 + 1; incr = d->step;  break;
    case DOWN_GT: start = d->N2;     end = d->N1;     incr = -d->step; break;
    case DOWN_GE: start = d->N2;     end = d->N1 - 1; incr = -d->step; break;
    }

  if (GOMP_loop_static_start (start, end, incr, 0, &istart, &iend))
    {
      do
	{
	  if (incr > 0)
	    {
	      for (i = istart; i < iend; i += d->step)
		d->b[i] = d->a[i];
	    }
	  else
	    {
	      for (i = istart; i > iend; i -= d->step)
		d->b[i] = d->a[i];
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

void
main1 (void)
{
  int i, N1, N2, step;
  int a[MAX], b[MAX];
  struct loop_ctx ctx;

  N1 = rand () % 13;
  N2 = rand () % (MAX - 51) + 50;
  step = rand () % 7 + 1;

  printf ("N1 = %d\nN2 = %d\nstep = %d\n", N1, N2, step);

  for (i = N1; i <= N2; i += step)
    a[i] = 42 + i;

  ctx.a = a;
  ctx.b = b;
  ctx.N1 = N1;
  ctx.N2 = N2;
  ctx.step = step;

  /* COUNTING UP (<) */
  memset (b, 0, sizeof b);
  ctx.mode = UP_LT;
  GOMP_parallel (loop_body, &ctx, 0, 0);
  for (i = N1; i < N2; i += step)
    if (a[i] != b[i])
      abort ();
  printf ("for (i = %d; i < %d; i += %d) [OK]\n", N1, N2, step);

  /* COUNTING UP (<=) */
  memset (b, 0, sizeof b);
  ctx.mode = UP_LE;
  GOMP_parallel (loop_body, &ctx, 0, 0);
  for (i = N1; i <= N2; i += step)
    if (a[i] != b[i])
      abort ();
  printf ("for (i = %d; i <= %d; i += %d) [OK]\n", N1, N2, step);

  /* COUNTING DOWN (>) */
  memset (b, 0, sizeof b);
  ctx.mode = DOWN_GT;
  GOMP_parallel (loop_body, &ctx, 0, 0);
  for (i = N2; i > N1; i -= step)
    if (a[i] != b[i])
      abort ();
  printf ("for (i = %d; i > %d; i -= %d) [OK]\n", N2, N1, step);

  /* COUNTING DOWN (>=) */
  memset (b, 0, sizeof b);
  ctx.mode = DOWN_GE;
  GOMP_parallel (loop_body, &ctx, 0, 0);
  for (i = N2; i >= N1; i -= step)
    if (a[i] != b[i])
      abort ();
  printf ("for (i = %d; i >= %d; i -= %d) [OK]\n", N2, N1, step);
}

int
main ()
{
  int i;
  srand (0);
  for (i = 0; i < 10; ++i)
    main1 ();
  return 0;
}
