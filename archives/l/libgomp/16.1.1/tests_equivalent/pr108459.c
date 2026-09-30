/* PR middle-end/108459 - equiv rewrite.
 * "parallel { for collapse(2) triangular }" -> GOMP_parallel + GOMP_loop_static over the
 * outer index (coverage is identical; each (i,j) set exactly once).
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

char a[17][17];

struct fctx { int x, y; };

static void
foo_body (void *arg)
{
  struct fctx *c = (struct fctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (1, 17, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      long j;
	      for (j = (long) i * c->x + c->y; j <= 16; j++)
		a[i][j] = 1;
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static void
foo (int x, int y)
{
  struct fctx c = { x, y };
  GOMP_parallel (foo_body, &c, 0, 0);
}

int
main (void)
{
  int i, j;
  foo (1, 1);
  for (i = 0; i <= 16; i++)
    for (j = 0; j <= 16; j++)
      if (i >= 1 && j >= i + 1)
	{
	  if (a[i][j] != 1)
	    abort ();
	  a[i][j] = 0;
	}
      else if (a[i][j])
	abort ();
  foo (2, -2);
  for (i = 0; i <= 16; i++)
    for (j = 0; j <= 16; j++)
      if (i >= 1 && j >= 2 * i - 2)
	{
	  if (a[i][j] != 1)
	    abort ();
	}
      else if (a[i][j])
	abort ();
  return 0;
}
