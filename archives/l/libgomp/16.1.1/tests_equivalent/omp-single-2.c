/* Equivalent rewrite: "parallel private(i,x) shared(bad) + single copyprivate(i,x)".
 * copyprivate is modeled as single_start + explicit barrier + a broadcast buffer
 * that lives on main's stack (avoids the copyprivate pointer-lifetime race). */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

struct X
{
  int a;
  char b;
  int c;
};

struct cp_data
{
  int i;
  struct X x;
};

struct s2_ctx
{
  int bad;
  struct cp_data cp;
};

static void
body (void *vp)
{
  struct s2_ctx *c = (struct s2_ctx *) vp;
  int i;
  struct X x;

  i = 5;

  if (GOMP_single_start ())
    {
      i++;
      x.a = 23;
      x.b = 42;
      x.c = 26;
      c->cp.i = i;
      c->cp.x = x;
    }
  GOMP_barrier ();

  i = c->cp.i;
  x = c->cp.x;

  if (i != 6 || x.a != 23 || x.b != 42 || x.c != 26)
    c->bad = 1;
}

int
main ()
{
  struct s2_ctx c;
  c.bad = 0;

  GOMP_parallel (body, &c, 0, 0);

  if (c.bad)
    abort ();

  return 0;
}
