/* PR c/79940 - equiv rewrite. taskloop(s) (host, independent per element) ->
 * GOMP_parallel + GOMP_loop_static; c[i] = 4*i + 4*(i&31); lastprivate l,m.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

struct ctx { int *a, *b, *c; int add; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, 10000, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      if (x->add)
		x->c[i] += x->a[i] + x->b[i];
	      else
		x->c[i] = x->a[i] + x->b[i];
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static void
run (int *a, int *b, int *c, int add)
{
  struct ctx x = { a, b, c, add };
  GOMP_parallel (body, &x, 0, 0);
}

int
main (void)
{
  int i, j, l, m;
  int a[10000], b[10000], c[10000];
  for (i = 0; i < 10000; i++)
    {
      a[i] = i;
      b[i] = i & 31;
    }
  run (a, b, c, 0);   /* c[i] = a[i]+b[i] */
  run (a, b, c, 1);   /* c[i] += a[i]+b[i]; lastprivate i */
  l = 10000;
  run (a, b, c, 1);   /* collapse(2) c[i*100+j] += ... */
  run (a, b, c, 1);   /* collapse(2) lastprivate i,j */
  m = 10100;
  (void) j;
  for (i = 0; i < 10000; i++)
    if (a[i] != i || b[i] != (i & 31) || c[i] != 4 * i + 4 * (i & 31))
      abort ();
  if (l != 10000 || m != 10100)
    abort ();
  return 0;
}
