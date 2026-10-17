/* Equiv-rewrite of upstream pr26943-4.c.
 * Outer: parallel num_threads(2) reduction(+:l) firstprivate(a,b,c,d,e,f,g,h,j).
 * Only the thread with k == thread_num runs the inner parallel-for, which then
 * operates on that thread's firstprivate COPIES; the globals stay unchanged.
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

struct inner_d {
  int *a; char *e; int *c; char *g; int *j;   /* shared / lastprivate / reduction targets */
  int *j_partials; long last_c; char last_g;
};

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
	    if (*d->a != 8 || bb != 12 || d->e[0] != 'a' || ff[0] != 'b')
	      jj++;
	    GOMP_barrier ();
	    GOMP_atomic_start (); *d->a += i; GOMP_atomic_end ();
	    bb += i;
	    cc = (int) i;
	    dd = (int) i;
	    GOMP_atomic_start (); d->e[0] += i; GOMP_atomic_end ();
	    ff[0] += i;
	    gg[0] = 'g' + i;
	    hh[0] = 'h' + i;
	    GOMP_barrier ();
	    if (*d->a != 8 + 6 || bb != 12 + i || cc != i || dd != i)
	      jj += 8;
	    if (d->e[0] != 'a' + 6 || ff[0] != 'b' + i || gg[0] != 'g' + i)
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
  /* firstprivate copies of the globals. */
  int aa = a, bb = b, cc = c, dd = d, jj = j;
  char ee[10], ff[10], gg[10], hh[10];
  memcpy (ee, e, sizeof ee);
  memcpy (ff, f, sizeof ff);
  memcpy (gg, g, sizeof gg);
  memcpy (hh, h, sizeof hh);

  if (k == tid)
    {
      int j_partials[4] = { 0, 0, 0, 0 };
      struct inner_d id = { &aa, ee, &cc, gg, &jj, j_partials, 16, 'c' };
      GOMP_parallel (inner_body, &id, 4, 0);
      int jsum = 0;
      for (int t = 0; t < 4; t++)
	jsum += j_partials[t];
      jj = jsum;            /* inner reduction write-back to outer copy j */
      cc = (int) id.last_c; /* lastprivate(c) */
      gg[0] = id.last_g;    /* lastprivate(g) */
      if (jj || aa != 8 + 6 || bb != 12 || cc != 3 || dd != 20)
	++ll;
      if (ee[0] != 'a' + 6 || ff[0] != 'b' || gg[0] != 'g' + 3 || hh[0] != 'd')
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
  if (a != 8 || b != 12 || c != 16 || d != 20)
    abort ();
  if (e[0] != 'a' || f[0] != 'b' || g[0] != 'c' || h[0] != 'd')
    abort ();
  return 0;
}
