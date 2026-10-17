/* Equiv-rewrite of upstream pr26943-2.c.
 * #pragma omp parallel for shared(a,e) firstprivate(b,f) lastprivate(c,g)
 * private(d,h) schedule(static,1) num_threads(4) reduction(+:j) over i in [0,4).
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

int a = 8, b = 12, c = 16, d = 20, j = 0;
char e[10] = "a", f[10] = "b", g[10] = "c", h[10] = "d";

struct dta { int *j_partials; long last_c; char last_g; };

static void
body (void *p)
{
  struct dta *d = (struct dta *) p;
  int tid = omp_get_thread_num ();
  int bb = 12;          /* firstprivate(b) */
  char ff[10] = "b";    /* firstprivate(f) */
  int dd;               /* private(d) */
  char hh[10];          /* private(h) */
  int cc;               /* private(c) -> lastprivate */
  char gg[10];          /* private(g) -> lastprivate */
  int jj = 0;           /* reduction(+:j) private accumulator */
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

int
main (void)
{
  omp_set_dynamic (0);
  int j_partials[4] = { 0, 0, 0, 0 };
  struct dta dt = { j_partials, 16, 'c' };
  GOMP_parallel (body, &dt, 4, 0);

  for (int t = 0; t < 4; t++)
    j += j_partials[t];
  c = (int) dt.last_c;   /* lastprivate(c) */
  g[0] = dt.last_g;      /* lastprivate(g) */

  if (j || a != 8 + 6 || b != 12 || c != 3 || d != 20)
    abort ();
  if (e[0] != 'a' + 6 || f[0] != 'b' || g[0] != 'g' + 3 || h[0] != 'd')
    abort ();
  return 0;
}
