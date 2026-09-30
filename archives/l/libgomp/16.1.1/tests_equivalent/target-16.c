extern void abort (void);

#include <stdbool.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_loop_static_start (long, long, long, long, long *, long *);
bool GOMP_loop_static_next (long *, long *);
void GOMP_loop_end (void);
void GOMP_atomic_start (void);
void GOMP_atomic_end (void);

struct bar_ctx { int n; int *a; int *err; };

static void
bar_parfor_init (void *d)
{
  struct bar_ctx *c = d;
  long istart, iend;
  int i;
  if (GOMP_loop_static_start (0, c->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    c->a[i] = 7 * i;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
bar_parfor_reduce (void *d)
{
  struct bar_ctx *c = d;
  long istart, iend;
  int i;
  int local_err = 0;
  if (GOMP_loop_static_start (0, c->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    if (c->a[i] != 7 * i)
	      local_err |= 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  GOMP_atomic_start ();
  *(c->err) |= local_err;
  GOMP_atomic_end ();
}

void
foo (int n)
{
  int a[n], i, err;
  for (i = 0; i < n; i++)
    a[i] = 7 * i;
  /* target firstprivate(a) map(from:err) private(i): host fallback;
     firstprivate(a) is a copy of a on host -> same values */
  {
    err = 0;
    for (i = 0; i < n; i++)
      if (a[i] != 7 * i)
	err = 1;
  }
  if (err)
    abort ();
}

void
bar (int n)
{
  int a[n], i, err;
  /* target private(a) map(from:err) with nested parallel for */
  {
    struct bar_ctx ctx = { n, a, &err };
    GOMP_parallel (bar_parfor_init, &ctx, 0, 0);
    err = 0;
    GOMP_parallel (bar_parfor_reduce, &ctx, 0, 0);
  }
  if (err)
    abort ();
}

int
main ()
{
  foo (7);
  bar (7);
  return 0;
}
