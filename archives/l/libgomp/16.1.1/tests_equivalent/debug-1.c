/* debug-1.c — 完全等价改写
 * f1..f7 的 parallel/single/sections/for/atomic/reduction 全部 outline 成 GOMP ABI。
 * main 无断言，仅需 rc=0。
 */
#include <stdlib.h>
#include <stdbool.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern bool GOMP_single_start (void);
extern unsigned GOMP_sections_start (unsigned);
extern unsigned GOMP_sections_next (void);
extern void GOMP_sections_end (void);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

int v2k = 9;
int v4k = 9, v4l = 0;
int v6k = 9, v6l = 0;

/* ---- f1: parallel private(v1k) firstprivate(v1j) shared(v1i) reduction(+:v1l) ---- */
struct f1d { int v1i; int v1j; int *partials; };

static void
f1_fn (void *arg)
{
  struct f1d *d = (struct f1d *) arg;
  int v1k;
  int v1j = d->v1j;		/* firstprivate */
  v1k = d->v1i + v1j;
  {
    int v1m = 1;
    d->partials[omp_get_thread_num ()] = v1m;	/* v1l = v1m */
  }
}

int
f1 (void)
{
  int v1i, v1j, v1k, v1l = 0;
  int maxn = omp_get_max_threads (), t;
  int *partials = (int *) calloc (maxn, sizeof (int));
  struct f1d d;
  v1i = 6;
  v1j = 8;
  d.v1i = v1i;
  d.v1j = v1j;
  d.partials = partials;
  GOMP_parallel (f1_fn, &d, 0, 0);
  for (t = 0; t < maxn; t++)
    v1l += partials[t];
  free (partials);
  return v1l;
}

/* ---- f2: 顶层 single private(v2i) firstprivate(v2k) ---- */
int
f2 (void)
{
  int v2i = 6, v2j = 7;
  if (GOMP_single_start ())
    {
      int v2i_priv;
      int v2k_priv = v2k;	/* firstprivate */
      int v2l = v2j + v2k_priv;
      v2i_priv = 8;
      v2k_priv = 10;
      v2j = v2l + v2i_priv;
    }
  return v2i + v2j;
}

/* ---- f3: parallel { master; single private(v3i) firstprivate(v3k); atomic v3k++ } ---- */
struct f3d { int *v3i; int *v3j; int *v3k; };

static void
f3_fn (void *arg)
{
  struct f3d *d = (struct f3d *) arg;
  if (omp_get_thread_num () == 0)
    (*d->v3i)++;
  if (GOMP_single_start ())
    {
      int v3i_priv;
      int v3k_priv = *d->v3k;	/* firstprivate */
      int v3l = *d->v3j + v3k_priv;
      v3i_priv = 8;
      v3k_priv = 10;
      *d->v3j = v3l + v3i_priv;
    }
  GOMP_barrier ();
  GOMP_atomic_start ();
  (*d->v3k)++;
  GOMP_atomic_end ();
}

int
f3 (void)
{
  int v3i = 6, v3j = 7, v3k = 9;
  struct f3d d = { &v3i, &v3j, &v3k };
  GOMP_parallel (f3_fn, &d, 0, 0);
  return v3i + v3j;
}

/* ---- f4: 顶层 sections private(v4i) firstprivate(v4k) reduction(+:v4l) ---- */
int
f4 (void)
{
  int v4i = 6, v4j = 7, v4n = 0;
  int v4l_local = 0;
  unsigned s;
  for (s = GOMP_sections_start (2); s != 0; s = GOMP_sections_next ())
    {
      if (s == 1)
	{
	  int v4i_priv;
	  int v4k_priv = v4k;
	  int v4m = v4j + v4k_priv;
	  v4i_priv = 8;
	  v4k_priv = 10;
	  v4l_local++;
	  v4n = v4m + v4i_priv;
	}
      else if (s == 2)
	{
	  int v4i_priv;
	  int v4k_priv = v4k;
	  int v4o = v4j + v4k_priv;
	  v4i_priv = 10;
	  v4k_priv = 11;
	  v4l_local++;
	}
    }
  GOMP_sections_end ();
  v4l += v4l_local;
  return v4i + v4j + v4l + v4n;
}

/* ---- f5: parallel { master; sections private(v5i) firstprivate(v5k) reduction(+:v5l) } ---- */
struct f5d { int *v5j; int *v5k; int *v5n; int *v5p; int *partials; };

static void
f5_fn (void *arg)
{
  struct f5d *d = (struct f5d *) arg;
  int v5l_local = 0;
  unsigned s;
  if (omp_get_thread_num () == 0)
    (*d->v5p)++;
  for (s = GOMP_sections_start (2); s != 0; s = GOMP_sections_next ())
    {
      if (s == 1)
	{
	  int v5i_priv;
	  int v5k_priv = *d->v5k;
	  int v5m = *d->v5j + v5k_priv;
	  v5i_priv = 8;
	  v5k_priv = 10;
	  v5l_local++;
	  *d->v5n = v5m + v5i_priv;
	}
      else if (s == 2)
	{
	  int v5i_priv;
	  int v5k_priv = *d->v5k;
	  int v5o = *d->v5j + v5k_priv;
	  v5i_priv = 10;
	  v5k_priv = 11;
	  v5l_local++;
	}
    }
  GOMP_sections_end ();
  d->partials[omp_get_thread_num ()] = v5l_local;
}

int
f5 (void)
{
  int v5i = 6, v5j = 7, v5k = 9, v5l = 0, v5n = 0, v5p = 0;
  int maxn = omp_get_max_threads (), t;
  int *partials = (int *) calloc (maxn, sizeof (int));
  struct f5d d = { &v5j, &v5k, &v5n, &v5p, partials };
  GOMP_parallel (f5_fn, &d, 0, 0);
  for (t = 0; t < maxn; t++)
    v5l += partials[t];
  free (partials);
  return v5i + v5j + v5l + v5n + v5p;
}

/* ---- f6: 顶层 for private(v6i) firstprivate(v6k) reduction(+:v6l) ---- */
int
f6 (void)
{
  int v6i = 6, v6j = 7, v6n = 0;
  int v6l_local = 0;
  long istart, iend;
  if (GOMP_loop_static_start (0, 3, 1, 0, &istart, &iend))
    {
      do
	{
	  for (v6n = istart; v6n < iend; v6n++)
	    {
	      int v6i_priv;
	      int v6k_priv = v6k;
	      int v6m = v6j + v6k_priv;
	      v6i_priv = 8;
	      v6l_local++;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  v6l += v6l_local;
  return v6i + v6j + v6k + v6l + v6n;
}

/* ---- f7: parallel { master; for private(v7i) firstprivate(v7k) reduction(+:v7l) } ---- */
struct f7d { int *v7j; int *v7k; int *v7o; int *partials; };

static void
f7_fn (void *arg)
{
  struct f7d *d = (struct f7d *) arg;
  int v7l_local = 0;
  long istart, iend;
  int v7n;
  if (omp_get_thread_num () == 0)
    (*d->v7o)++;
  if (GOMP_loop_static_start (0, 3, 1, 0, &istart, &iend))
    {
      do
	{
	  for (v7n = istart; v7n < iend; v7n++)
	    {
	      int v7i_priv;
	      int v7k_priv = *d->v7k;
	      int v7m = *d->v7j + v7k_priv;
	      v7i_priv = 8;
	      v7l_local++;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->partials[omp_get_thread_num ()] = v7l_local;
}

int
f7 (void)
{
  int v7i = 6, v7j = 7, v7k = 9, v7l = 0, v7n = 0, v7o = 1;
  int maxn = omp_get_max_threads (), t;
  int *partials = (int *) calloc (maxn, sizeof (int));
  struct f7d d = { &v7j, &v7k, &v7o, partials };
  GOMP_parallel (f7_fn, &d, 0, 0);
  for (t = 0; t < maxn; t++)
    v7l += partials[t];
  free (partials);
  return v7i + v7j + v7k + v7l + v7n;
}

int
main (void)
{
  f1 ();
  f2 ();
  f3 ();
  f4 ();
  f5 ();
  f6 ();
  f7 ();
  return 0;
}
