/* Equiv-rewrite of upstream atomic-14.c: atomic with function calls, wrap verbatim. */
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
  GOMP_atomic_start (); x = x + 7; GOMP_atomic_end ();
  GOMP_atomic_start (); x = x + (7 + 6); GOMP_atomic_end ();
  GOMP_atomic_start (); x = x + 2 * 3; GOMP_atomic_end ();
  GOMP_atomic_start (); x = x * (2 - 1); GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 32)
    abort ();
  GOMP_atomic_start (); x = 0; GOMP_atomic_end ();
  GOMP_atomic_start ();
  {
    v = x;
    x = x | 1 ^ 2;
  }
  GOMP_atomic_end ();
  if (v != 0)
    abort ();
  GOMP_atomic_start ();
  {
    v = x;
    x = x | 4 | 2;
  }
  GOMP_atomic_end ();
  if (v != 3)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 7)
    abort ();
  GOMP_atomic_start ();
  {
    x = x ^ 6 & 2;
    v = x;
  }
  GOMP_atomic_end ();
  if (v != 5)
    abort ();
  GOMP_atomic_start (); { x = x - (6 + 4); v = x; } GOMP_atomic_end ();
  if (v != -5)
    abort ();
  GOMP_atomic_start (); { v = x; x = x - (1 | 2); } GOMP_atomic_end ();
  if (v != -5)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != -8)
    abort ();
  GOMP_atomic_start (); x = x * (-4 / 2); GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 16)
    abort ();
  p = &x;
  GOMP_atomic_start (); p[foo (), 0] = p[foo (), 0] - 16; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (cnt != 2 || v != 0)
    abort ();
  GOMP_atomic_start ();
  {
    p[foo (), 0] += 6;
    v = p[foo (), 0];
  }
  GOMP_atomic_end ();
  if (cnt != 4 || v != 6)
    abort ();
  GOMP_atomic_start ();
  {
    v = p[foo (), 0];
    p[foo (), 0] += 6;
  }
  GOMP_atomic_end ();
  if (cnt != 6 || v != 6)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 12)
    abort ();
  GOMP_atomic_start ();
  {
    p[foo (), 0] = p[foo (), 0] + 6;
    v = p[foo (), 0];
  }
  GOMP_atomic_end ();
  if (cnt != 9 || v != 18)
    abort ();
  GOMP_atomic_start ();
  {
    v = p[foo (), 0];
    p[foo (), 0] = p[foo (), 0] + 6;
  }
  GOMP_atomic_end ();
  if (cnt != 12 || v != 18)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 24)
    abort ();
  GOMP_atomic_start (); { v = p[foo (), 0]; p[foo (), 0]++; } GOMP_atomic_end ();
  GOMP_atomic_start (); { v = p[foo (), 0]; ++p[foo (), 0]; } GOMP_atomic_end ();
  GOMP_atomic_start (); { p[foo (), 0]++; v = p[foo (), 0]; } GOMP_atomic_end ();
  GOMP_atomic_start (); { ++p[foo (), 0]; v = p[foo (), 0]; } GOMP_atomic_end ();
  if (cnt != 20 || v != 28)
    abort ();
  GOMP_atomic_start (); { v = p[foo (), 0]; p[foo (), 0]--; } GOMP_atomic_end ();
  GOMP_atomic_start (); { v = p[foo (), 0]; --p[foo (), 0]; } GOMP_atomic_end ();
  GOMP_atomic_start (); { p[foo (), 0]--; v = p[foo (), 0]; } GOMP_atomic_end ();
  GOMP_atomic_start (); { --p[foo (), 0]; v = p[foo (), 0]; } GOMP_atomic_end ();
  if (cnt != 28 || v != 24)
    abort ();
  return 0;
}
