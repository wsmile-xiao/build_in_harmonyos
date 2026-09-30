/* Equiv-rewrite of upstream atomic-16.c: atomic with comma/fn calls, wrap verbatim. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int x = 6, cnt;

int
foo (void)
{
  return cnt++;
}

int
main ()
{
  int v, *p;
  p = &x;
  GOMP_atomic_start (); p[foo (), 0] = 16 + 6 - p[foo (), 0]; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (cnt != 2 || v != 16)
    abort ();
  GOMP_atomic_start (); v = p[foo () + foo (), 0] = p[foo () + foo (), 0] + 3; GOMP_atomic_end ();
  if (cnt != 6 || v != 19)
    abort ();
  GOMP_atomic_start (); v = p[foo (), 0] = 12 * 1 / 2 + (foo (), 0) + p[foo (), 0]; GOMP_atomic_end ();
  if (cnt != 9 || v != 25)
    abort ();
  GOMP_atomic_start ();
  {
    v = p[foo () & 0]; p[foo () & 0] = (foo (), 1) * 9 - p[foo () & 0];
  }
  GOMP_atomic_end ();
  if (cnt != 13 || v != 25)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != -16)
    abort ();
  GOMP_atomic_start ();
  {
    p[0 & foo ()] = 16 - 2 + 3 + p[0 & foo ()]; v = p[0 & foo ()];
  }
  GOMP_atomic_end ();
  if (cnt != 16 || v != 1)
    abort ();
  GOMP_atomic_start ();
  {
    v = p[foo (), 0]; p[foo (), 0] = (foo (), 7) ? 13 : foo () + 6;
  }
  GOMP_atomic_end ();
  if (cnt != 19 || v != 1)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 13)
    abort ();
  return 0;
}
