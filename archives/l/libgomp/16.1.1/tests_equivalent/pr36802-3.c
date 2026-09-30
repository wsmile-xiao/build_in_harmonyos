/* PR middle-end/36802 (nested parallel inside for, inverted branch) - equiv rewrite.
 * foo(0): outer parallel(3) { for l: nested parallel(4) { critical i++ } } -> i = 6 + 3*4.
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
extern void GOMP_critical_start (void);
extern void GOMP_critical_end (void);

int q;

struct ctx { int *i; int *n; int k; };

static void
inner_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  if (omp_get_num_threads () != 4)
    { GOMP_atomic_start (); (*x->n) += 1; GOMP_atomic_end (); }
  GOMP_critical_start (); (*x->i) += 1; GOMP_critical_end ();
}

static void
outer_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  if (omp_get_num_threads () != 3)
    { GOMP_atomic_start (); (*x->n) += 1; GOMP_atomic_end (); }
  else
    {
      long lst, len;
      if (GOMP_loop_static_start (0, 3, 1, 0, &lst, &len))
	{
	  do
	    {
	      long l;
	      for (l = lst; l < len; l++)
		{
		  if (!x->k)
		    GOMP_parallel (inner_body, x, 4, 0);
		  else
		    { GOMP_atomic_start (); q += (*x->i); GOMP_atomic_end (); }
		}
	    }
	  while (GOMP_loop_static_next (&lst, &len));
	}
      GOMP_loop_end ();
    }
}

static int
foo (int k)
{
  int i = 6, n = 0;
  struct ctx x = { &i, &n, k };
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_parallel (outer_body, &x, 3, 0);
  if (n == 0 && i != 6 + 3 * 4)
    abort ();
  return 0;
}

int
main (void)
{
  foo (0);
  return 0;
}
