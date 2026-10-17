/* Equiv-rewrite of upstream pr26943-3.c.
 * Outer: parallel num_threads(2) reduction(+:l); only the thread with
 * k == thread_num runs the inner parallel-for (same as pr26943-2).
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>

extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

int a = 8, b = 12, c = 16, d = 20, j = 0, l = 0;
char e[10] = "a", f[10] = "b", g[10] = "c", h[10] = "d";
volatile int k;

struct inner_d { int *j_partials; long last_c; char last_g; };

static void
inner_body (void *p)
{
  struct inner_d *d = (struct inner_d *) p;
  int tid = omp_get_thread_num ();
  int bb = 12;
  char ff[10] = "b";
  int dd;
  char hh[10];
  int cc;
  char gg[10];
  int jj = 0;
  long istart, iend;
  if (GOMP_loop_static_start (0, 4, 1, 1, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  {
	    if (a != 8 || bb != 12 || e[0] != 'a' || ff[0] != 'b')
	      jj++;
	    GOMP_barrier ();
	    GOMP_atomic_start (); a += i; GOMP_atomic_end ();
	    bb += i;
	    cc = (int) i;
	    dd = (int) i;
	    GOMP_atomic_start (); e[0] += i; GOMP_atomic_end ();
	    ff[0] += i;
	    gg[0] = 'g' + i;
	    hh[0] = 'h' + i;
	    GOMP_barrier ();
	    if (a != 8 + 6 || bb != 12 + i || cc != i || dd != i)
	      jj += 8;
	    if (e[0] != 'a' + 6 || ff[0] != 'b' + i || gg[0] != 'g' + i)
	      jj += 64;
	    if (hh[0] != 'h' + i)
	      jj += 512;
	    if (i == 3)
	      { d->last_c = cc; d->last_g = gg[0]; }
	  }
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->j_partials[tid] = jj;
}

struct outer_d { long l_partials[2]; };

static void
outer_body (void *p)
{
  struct outer_d *od = (struct outer_d *) p;
  int tid = omp_get_thread_num ();
  long ll = 0;
  if (k == tid)
    {
      int j_partials[4] = { 0, 0, 0, 0 };
      struct inner_d id = { j_partials, 16, 'c' };
      GOMP_parallel (inner_body, &id, 4, 0);
      int jsum = 0;
      for (int t = 0; t < 4; t++)
	jsum += j_partials[t];
      c = (int) id.last_c;   /* lastprivate(c) */
      g[0] = id.last_g;      /* lastprivate(g) */
      if (jsum || a != 8 + 6 || b != 12 || c != 3 || d != 20)
	++ll;
      if (e[0] != 'a' + 6 || f[0] != 'b' || g[0] != 'g' + 3 || h[0] != 'd')
	ll += 8;
    }
  od->l_partials[tid] = ll;
}

int
main (void)
{
  omp_set_dynamic (0);
  omp_set_nested (1);
  struct outer_d od = { { 0, 0 } };
  GOMP_parallel (outer_body, &od, 2, 0);
  long lsum = od.l_partials[0] + od.l_partials[1];
  if (lsum)
    abort ();
  return 0;
}
