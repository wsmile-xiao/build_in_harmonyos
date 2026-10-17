/* Equiv-rewrite of upstream pr93566.c.
 * GNU nested fns -> static fns + pointer args.
 * #pragma omp parallel for reduction(+:x[lo:len]) -> GOMP_parallel +
 *   GOMP_loop_static_* over i, each thread accumulates into a private
 *   per-thread copy of the array section, then master sums back.
 * Array sections x[:10], x[2:5], x[:7], x[:9] map to [lo,hi) ranges.
 */
#include <omp.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 128
#define MAXW 10

struct rdata {
  int *x;              /* base of reduction section */
  int lo, hi;          /* section [lo, hi) */
  int (*priv)[MAXW];   /* per-thread private copies (MAXT x MAXW) */
};

static void rbody (void *p)
{
  struct rdata *d = (struct rdata *) p;
  int tn = omp_get_thread_num ();
  long i, istart, iend;
  if (GOMP_loop_static_start (0, 1024, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      int j;
	      for (j = d->lo; j < d->hi; j++)
		d->priv[tn][j] += j * (int) i;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void reduce (struct rdata *d)
{
  int j, t;
  for (j = d->lo; j < d->hi; j++)
    {
      int s = 0;
      for (t = 0; t < MAXT; t++)
	s += d->priv[t][j];
      d->x[j] += s;
    }
}

#define EXPECT(j) (1023 * 1024 / 2 * (j))

static void foo (int *x)
{
  int priv[MAXT][MAXW];
  struct rdata d = { x, 0, 10, priv };
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  for (int i = 0; i < 10; i++)
    if (x[i] != EXPECT (i))
      abort ();
}

static void bar (void)
{
  int x[10] = {0};
  int priv[MAXT][MAXW];
  struct rdata d = { x, 0, 10, priv };
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  for (int i = 0; i < 10; i++)
    if (x[i] != EXPECT (i))
      abort ();
}

static void baz (void)
{
  int x[10] = {0};
  int priv[MAXT][MAXW];
  struct rdata d = { x, 2, 7, priv };
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  for (int i = 2; i < 7; i++)
    if (x[i] != EXPECT (i))
      abort ();
}

static void qux (int *x)
{
  int priv[MAXT][MAXW];
  struct rdata d;
  x++;                        /* nest() { x++; } */
  d.x = x; d.lo = 0; d.hi = 9; d.priv = priv;
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  x++;                        /* nest() { x++; } */
  for (int i = 0; i < 9; i++)
    if (x[i - 1] != EXPECT (i))
      abort ();
}

static void quux (void)
{
  int x[10];
  int priv[MAXT][MAXW];
  struct rdata d;
  for (int i = 0; i < 10; i++)
    x[i] = 0;                 /* nest() { zero } */
  d.x = x; d.lo = 0; d.hi = 7; d.priv = priv;
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  for (int i = 0; i < 7; i++)
    if (x[i] != EXPECT (i))
      abort ();
}

static void corge (void)
{
  int x[10];
  int priv[MAXT][MAXW];
  struct rdata d;
  for (int i = 0; i < 10; i++)
    x[i] = 0;
  d.x = x; d.lo = 2; d.hi = 6; d.priv = priv;
  memset (priv, 0, sizeof priv);
  GOMP_parallel (rbody, &d, 0, 0);
  reduce (&d);
  for (int i = 2; i < 6; i++)
    if (x[i] != EXPECT (i))
      abort ();
}

int main (void)
{
  int a[10] = {0};
  foo (a);
  bar ();
  baz ();
  for (int i = 0; i < 10; i++)
    a[i] = 0;
  qux (a);
  quux ();
  corge ();
  return 0;
}
