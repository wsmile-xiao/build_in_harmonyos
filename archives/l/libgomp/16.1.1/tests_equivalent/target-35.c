// { dg-additional-options "-Wno-deprecated-openmp" }
#include <omp.h>
#include <stdlib.h>
#include <stdbool.h>

void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);
void GOMP_teams_reg (void (*)(void *), void *, unsigned, unsigned, unsigned);
void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_loop_static_start (long, long, long, long, long *, long *);
bool GOMP_loop_static_next (long *, long *);
void GOMP_loop_end (void);
void GOMP_atomic_start (void);
void GOMP_atomic_end (void);

static int err;

static void
foo3 (int y, int z, int *a, int *b)
{
  GOMP_atomic_start ();
  b[y] += z;
  GOMP_atomic_end ();
  GOMP_atomic_start ();
  *a += 1;
  GOMP_atomic_end ();
}

struct pj_ctx { int y; int *a; int *b; };

static void
parfor_j (void *d)
{
  struct pj_ctx *c = d;
  long istart, iend;
  int j;
  if (GOMP_loop_static_start (0, 32, 1, 0, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    foo3 (c->y, j, c->a, c->b);
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
      for (int i = 0; i < 64; i++)
	{
	  struct pj_ctx c = { i, a, b };
	  GOMP_parallel (parfor_j, &c, 0, 0);
	}
    }
  else if (x == 1)
    {
      int nt = omp_get_num_teams ();
      int tn = omp_get_team_num ();
      for (int i = tn; i < 64; i += nt)
	{
	  struct pj_ctx c = { i, a, b };
	  GOMP_parallel (parfor_j, &c, 0, 0);
	}
    }
  else if (x == 2)
    {
      struct pj_ctx c = { y, a, b };
      GOMP_parallel (parfor_j, &c, 0, 0);
    }
  else
    foo3 (y, z, a, b);
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

/* teams reduction(+:err) bodies */
static void teams1 (void *d) { (void)d; int e = 0; e += bar (0, 0, 0); GOMP_atomic_start (); err += e; GOMP_atomic_end (); }
static void teams2 (void *d) { (void)d; int e = 0; e += bar (1, 0, 0); GOMP_atomic_start (); err += e; GOMP_atomic_end (); }

static void teams3 (void *d)
{
  (void)d;
  int nt = omp_get_num_teams ();
  int tn = omp_get_team_num ();
  int e = 0;
  for (int i = tn; i < 64; i += nt)
    e += bar (2, i, 0);
  GOMP_atomic_start (); err += e; GOMP_atomic_end ();
}

struct p4_ctx { int i; int *errp; };

static void p4_body (void *d)
{
  struct p4_ctx *c = d;
  long istart, iend;
  int j;
  int elocal = 0;
  if (GOMP_loop_static_start (0, 32, 1, 0, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    elocal += bar (3, c->i, j);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  GOMP_atomic_start (); *(c->errp) += elocal; GOMP_atomic_end ();
}

static void teams4 (void *d)
{
  (void)d;
  int nt = omp_get_num_teams ();
  int tn = omp_get_team_num ();
  int e = 0;
  for (int i = tn; i < 64; i += nt)
    {
      struct p4_ctx c = { i, &e };
      GOMP_parallel (p4_body, &c, 0, 0);
    }
  GOMP_atomic_start (); err += e; GOMP_atomic_end ();
}

static void tgt1 (void *d) { (void)d; GOMP_teams_reg (teams1, NULL, 0, 0, 0); }
static void tgt2 (void *d) { (void)d; GOMP_teams_reg (teams2, NULL, 0, 0, 0); }
static void tgt3 (void *d) { (void)d; GOMP_teams_reg (teams3, NULL, 0, 0, 0); }
static void tgt4 (void *d) { (void)d; GOMP_teams_reg (teams4, NULL, 0, 0, 0); }

int
main ()
{
  err = 0;
  GOMP_target (-1, tgt1, NULL, 0, NULL, NULL, NULL);
  if (err)
    abort ();
  GOMP_target (-1, tgt2, NULL, 0, NULL, NULL, NULL);
  if (err)
    abort ();
  GOMP_target (-1, tgt3, NULL, 0, NULL, NULL, NULL);
  if (err)
    abort ();
  GOMP_target (-1, tgt4, NULL, 0, NULL, NULL, NULL);
  if (err)
    abort ();
  return 0;
}
