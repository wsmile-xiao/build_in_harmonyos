/* PR middle-end/30494 - equiv rewrite.
 * parallel (3) { #pragma omp for (foo) ; #pragma omp parallel for num_threads(4) (bar) }
 * with per-iteration VLAs -> GOMP_parallel + GOMP_loop_static.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static int errors;

static void
do_check (int m, int i, int *v, int *w)
{
  int n = omp_get_thread_num ();
  int j;
  for (j = 0; j < m; j++)
    if (v[j] != j + n)
      { GOMP_atomic_start (); errors += 1; GOMP_atomic_end (); }
  for (j = 0; j < m * 3 + i; j++)
    if (w[j] != j + 10 + n)
      { GOMP_atomic_start (); errors += 1; GOMP_atomic_end (); }
}

struct fctx { int n, m; };

/* foo: #pragma omp for (orphaned, inside the outer parallel region) */
static void
foo_body (void *arg)
{
  struct fctx *x = (struct fctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, 6, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      int v[x->n], w[x->n * 3 + i], j;
	      for (j = 0; j < x->n; j++)
		v[j] = j + omp_get_thread_num ();
	      for (j = 0; j < x->n * 3 + i; j++)
		w[j] = j + 10 + omp_get_thread_num ();
	      do_check (x->m, (int) i, v, w);
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

/* bar: #pragma omp parallel for num_threads(4) (nested) */
static void
bar_body (void *arg)
{
  struct fctx *x = (struct fctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, 6, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      int v[x->n], w[x->n * 3 + i], j;
	      for (j = 0; j < x->n; j++)
		v[j] = j + omp_get_thread_num ();
	      for (j = 0; j < x->n * 3 + i; j++)
		w[j] = j + 10 + omp_get_thread_num ();
	      do_check (x->m, (int) i, v, w);
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static void
bar_outer (void *arg)
{
  GOMP_parallel (bar_body, arg, 4, 0);
}

static void
main_body (void *arg)
{
  struct fctx f = { 128, 128 };
  struct fctx b = { 256, 256 };
  foo_body (&f);
  bar_outer (&b);
}

int
main (void)
{
  GOMP_parallel (main_body, 0, 3, 0);
  return 0;
}
