/* PR middle-end/39154 - equiv rewrite.
 * Nested "parallel for" over VLA a[n], b[n][n] -> GOMP_parallel + GOMP_loop_static.
 * b flattened to b[i*n + j].
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

static int n = 20;

struct ctx { int *a; int *b; int val; int i; };

static void
inner_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long jst, jen;
  if (GOMP_loop_static_start (0, n, 1, 0, &jst, &jen))
    {
      do
	{
	  long j;
	  for (j = jst; j < jen; j++)
	    x->b[x->i * n + j] = x->a[x->i];
	}
      while (GOMP_loop_static_next (&jst, &jen));
    }
  GOMP_loop_end ();
}

static void
outer_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, n, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      struct ctx ic = *x;
	      x->a[i] = (int) i + x->val;
	      ic.i = (int) i;
	      GOMP_parallel (inner_body, &ic, 0, 0);
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static void
run_checked (int *a, int *b, int val)
{
  struct ctx x = { a, b, val, 0 };
  GOMP_parallel (outer_body, &x, 0, 0);
  for (int i = 0; i < n; i++)
    {
      for (int j = 0; j < n; j++)
	if (b[i * n + j] != i + val)
	  abort ();
      if (a[i] != i + val)
	abort ();
    }
}

/* private(a,b) variants: no observable check, only exercise private VLAs. */
static void
priv_body (void *arg)
{
  (void) arg;
  int a[n], b[n * n];
  long ist, ien;
  if (GOMP_loop_static_start (0, n, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      a[i] = (int) i + 1;
	      for (int j = 0; j < n; j++)
		b[i * n + j] = a[i];
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int a[n], b[n * n];
  run_checked (a, b, 1);
  run_checked (a, b, 3);
  run_checked (a, b, 5);
  run_checked (a, b, 7);
  GOMP_parallel (priv_body, 0, 0, 0);
  GOMP_parallel (priv_body, 0, 0, 0);
  return 0;
}
