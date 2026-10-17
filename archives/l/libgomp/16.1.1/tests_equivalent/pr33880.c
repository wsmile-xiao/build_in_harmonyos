/* Equiv-rewrite of upstream pr33880.c.
 * GNU nested fns -> static fns + pointer args.
 * #pragma omp parallel for [lastprivate(i)] -> GOMP_parallel + GOMP_loop_static_*.
 * #pragma omp atomic -> GOMP_atomic_start/end.
 * lastprivate loop var -> max of per-thread final loop-var values.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 128

/* ---- generic parallel-for with atomic counter increment ---- */
struct loop_ctx {
  int *counter;         /* shared counter to atomic-increment */
  long start, end, incr;
  long *last_priv;      /* optional per-thread final i (lastprivate) */
};

static void loop_body (void *p)
{
  struct loop_ctx *d = (struct loop_ctx *) p;
  int tn = omp_get_thread_num ();
  long i, istart, iend;
  if (GOMP_loop_static_start (d->start, d->end, d->incr, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i += d->incr)
	    {
	      GOMP_atomic_start ();
	      (*d->counter)++;
	      GOMP_atomic_end ();
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
      if (d->last_priv)
	d->last_priv[tn] = i;
    }
  GOMP_loop_end ();
}

/* run the loop; if last_priv non-NULL, return the lastprivate value */
static long run_loop (int *counter, long start, long end, long incr,
		      unsigned nt, long *last_priv)
{
  struct loop_ctx d = { counter, start, end, incr, last_priv };
  long f;
  int t;
  if (last_priv)
    for (t = 0; t < MAXT; t++)
      last_priv[t] = start;
  GOMP_parallel (loop_body, &d, nt, 0);
  if (!last_priv)
    return 0;
  f = last_priv[0];
  for (t = 1; t < MAXT; t++)
    if (last_priv[t] > f)
      f = last_priv[t];
  return f;
}

/* ---- test1 ---- */
static void test1_bar (int *i, int *j) { (*i)++; (*j)++; }

static void test1 (void)
{
  int i = 0, j = 0;
  long last_priv[MAXT];
  test1_bar (&i, &j);             /* i=1, j=1 */
  run_loop (&j, 0, 100, 1, 4, 0); /* j += 100 -> 101 */
  if (j != 101)
    abort ();
  i = (int) run_loop (&j, 0, 100, 1, 2, last_priv); /* j += 100 -> 201; i=100 */
  if (i != 100)
    abort ();
  i = 3;
  test1_bar (&i, &j);             /* i=4, j=202 */
  if (j != 202)
    abort ();
  if (i != 4)
    abort ();
}

/* ---- test2 ---- */
static void test2_bar (int *i, int *j, int *l, int *m)
{ (*i)++; (*j)++; (*l)++; (*m)++; }

static void test2 (void)
{
  int i = -1, j = 99, k, l = 9, m = 0;
  test2_bar (&i, &j, &l, &m);     /* i=0,j=100,l=10,m=1 */
  run_loop (&m, i, j, l, 4, 0);   /* k=0..90 step10 -> 10 iters -> m=11 */
  test2_bar (&i, &j, &l, &m);     /* i=1,j=101,l=11,m=12 */
  if (i != 1 || j != 101 || l != 11 || m != 12)
    abort ();
}

/* ---- test3 ---- */
static void test3_bar (int *j, int *k, int *l, int *m)
{
  run_loop (m, *j, *k, *l, 4, 0);  /* loop var is private, no lastprivate */
}
static void test3_baz (int *j, int *k, int *l, int *m, int *i)
{
  long lp[MAXT];
  *i = (int) run_loop (m, *j, (long) *k * 2, (long) *l / 2, 2, lp);
}

static void test3 (void)
{
  int i, j, k, l, m;
  i = 7; j = 0; k = 100; l = 2; m = 0;
  test3_bar (&j, &k, &l, &m);        /* m=50, i unchanged */
  if (j != 0 || k != 100 || l != 2 || m != 50)
    abort ();
  test3_baz (&j, &k, &l, &m, &i);    /* m=250, lastprivate i=200 */
  if (i != 200 || j != 0 || k != 100 || l != 2 || m != 250)
    abort ();
}

/* ---- test4 ---- */
static int t4_foo (int *j) { return *j; }
static int t4_bar (int *k) { return *k; }
static int t4_baz (int *l) { return *l; }

static void test4 (void)
{
  int i, j, k, l, m = 0;
  long lp[MAXT];
  j = 0; k = 1000; l = 2;
  i = (int) run_loop (&m, t4_foo (&j), t4_bar (&k), t4_baz (&l), 8, lp);
  if (i != 1000 || m != 500 || j != 0 || k != 1000 || l != 2)
    abort ();
}

int main (void)
{
  test1 ();
  test2 ();
  test3 ();
  test4 ();
  return 0;
}
