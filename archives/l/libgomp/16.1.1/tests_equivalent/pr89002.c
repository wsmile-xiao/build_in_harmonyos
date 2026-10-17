/* PR middle-end/89002 - equiv rewrite. taskloop lastprivate(a) with empty body
 * -> a == x (loop-exit value); parallel+single wrapper for bar.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);

static int
foo (int x)
{
  int a;
  int *p = &a;
  for (a = 0; a < x; ++a)
    ;
  return *p;
}

struct bctx { int x; int *result; };

static void
bar_single (void *arg)
{
  struct bctx *b = (struct bctx *) arg;
  int a;
  int *p = &a;
  for (a = 0; a < b->x; ++a)
    ;
  *b->result = *p;
}

static void
bar_par (void *arg)
{
  if (GOMP_single_start ())
    bar_single (arg);
}

static int
bar (int x)
{
  int r = 0;
  struct bctx b = { x, &r };
  GOMP_parallel (bar_par, &b, 0, 0);
  return r;
}

static void
main_single (void *arg)
{
  (void) arg;
  if (foo (4) != 4)
    abort ();
}

static void
main_par (void *arg)
{
  if (GOMP_single_start ())
    main_single (arg);
}

int
main (void)
{
  GOMP_parallel (main_par, 0, 0, 0);
  if (bar (6) != 6)
    abort ();
  return 0;
}
