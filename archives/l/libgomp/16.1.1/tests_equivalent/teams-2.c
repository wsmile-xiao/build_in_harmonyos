/* Equivalent rewrite: teams / distribute / parallel-for / atomic -> GOMP_teams_reg + GOMP_parallel + GOMP_atomic */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

static void foo (int x, int y, int z, int *a, int *b);

struct pf_ctx
{
  int i;
  int *a;
  int *b;
};

static void
pf_fn (void *vp)
{
  struct pf_ctx *c = (struct pf_ctx *) vp;
  int j;
  long istart, iend;

  if (GOMP_loop_static_start (0, 32, 1, 0, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    foo (3, c->i, j, c->a, c->b);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
foo (int x, int y, int z, int *a, int *b)
{
  if (x == 0)
    {
      int i;
      for (i = 0; i < 64; i++)
	{
	  struct pf_ctx ctx = { i, a, b };
	  GOMP_parallel (pf_fn, &ctx, 0, 0);
	}
    }
  else if (x == 1)
    {
      int c = omp_get_num_teams ();
      int d = omp_get_team_num ();
      int i;
      for (i = d; i < 64; i += c)
	{
	  struct pf_ctx ctx = { i, a, b };
	  GOMP_parallel (pf_fn, &ctx, 0, 0);
	}
    }
  else if (x == 2)
    {
      struct pf_ctx ctx = { y, a, b };
      GOMP_parallel (pf_fn, &ctx, 0, 0);
    }
  else
    {
      GOMP_atomic_start ();
      b[y] += z;
      GOMP_atomic_end ();
      GOMP_atomic_start ();
      *a += 1;
      GOMP_atomic_end ();
    }
}

static int
bar (int x, int y, int z)
{
  int a, b[64], i;
  a = 8;
  for (i = 0; i < 64; i++)
    b[i] = i;
  foo (x, y, z, &a, b);

  if (x == 0)
    {
      if (a != 8 + 64 * 32)
	return 1;
      for (i = 0; i < 64; i++)
	if (b[i] != i + 31 * 32 / 2)
	  return 1;
    }
  else if (x == 1)
    {
      int c = omp_get_num_teams ();
      int d = omp_get_team_num ();
      int e = d;
      int f = 0;
      for (i = 0; i < 64; i++)
	if (i == e)
	  {
	    if (b[i] != i + 31 * 32 / 2)
	      return 1;
	    f++;
	    e = e + c;
	  }
	else if (b[i] != i)
	  return 1;
      if (a < 8 || a > 8 + f * 32)
	return 1;
    }
  else if (x == 2)
    {
      if (a != 8 + 32)
	return 1;
      for (i = 0; i < 64; i++)
	if (b[i] != i + (i == y ? 31 * 32 / 2 : 0))
	  return 1;
    }
  else if (x == 3)
    {
      if (a != 8 + 1)
	return 1;
      for (i = 0; i < 64; i++)
	if (b[i] != i + (i == y ? z : 0))
	  return 1;
    }
  return 0;
}

static void
team_fn0 (void *vp)
{
  int *err = (int *) vp;
  int local = 0;
  local += bar (0, 0, 0);
  GOMP_atomic_start ();
  *err += local;
  GOMP_atomic_end ();
}

static void
team_fn1 (void *vp)
{
  int *err = (int *) vp;
  int local = 0;
  local += bar (1, 0, 0);
  GOMP_atomic_start ();
  *err += local;
  GOMP_atomic_end ();
}

static void
team_fn2 (void *vp)
{
  int *err = (int *) vp;
  int c = omp_get_num_teams ();
  int d = omp_get_team_num ();
  int local = 0, i;
  for (i = d; i < 64; i += c)
    local += bar (2, i, 0);
  GOMP_atomic_start ();
  *err += local;
  GOMP_atomic_end ();
}

struct pf3_ctx
{
  int i;
  int *team_err;
};

static void
pf3_fn (void *vp)
{
  struct pf3_ctx *c = (struct pf3_ctx *) vp;
  int j;
  int local = 0;
  long istart, iend;

  if (GOMP_loop_static_start (0, 32, 1, 0, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    local += bar (3, c->i, j);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  GOMP_atomic_start ();
  *c->team_err += local;
  GOMP_atomic_end ();
}

static void
team_fn3 (void *vp)
{
  int *err = (int *) vp;
  int c = omp_get_num_teams ();
  int d = omp_get_team_num ();
  int local = 0, i;
  for (i = d; i < 64; i += c)
    {
      struct pf3_ctx pctx = { i, &local };
      GOMP_parallel (pf3_fn, &pctx, 0, 0);
    }
  GOMP_atomic_start ();
  *err += local;
  GOMP_atomic_end ();
}

int
main ()
{
  int err = 0;

  GOMP_teams_reg (team_fn0, &err, 0, 0, 0);
  if (err)
    abort ();

  GOMP_teams_reg (team_fn1, &err, 0, 0, 0);
  if (err)
    abort ();

  GOMP_teams_reg (team_fn2, &err, 0, 0, 0);
  if (err)
    abort ();

  GOMP_teams_reg (team_fn3, &err, 0, 0, 0);
  if (err)
    abort ();

  return 0;
}
