/* Equiv-rewrite of upstream pr122852.c (dg-do compile: a GCC -O2 -fopenmp ICE
 * regression; the original has no main, so it only compiles). We add a main()
 * and lower the dead `#pragma omp parallel while(a);` to a GOMP_parallel
 * outline so the program links and runs with rc=0.
 */
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

int a, b, c;

static void
spin_body (void *p)
{
  (void) p;
  while (a)
    ;
}

static void
foo (int g)
{
  int f = c ? c : 2;
  if (c)
    b = 3;
  if (!g)
    for (int d = 0; d < f; ++d)
      GOMP_parallel (spin_body, 0, 0, 0);
}

void
bar (void)
{
  foo (1);
}

int
main (void)
{
  bar ();
  return 0;
}
