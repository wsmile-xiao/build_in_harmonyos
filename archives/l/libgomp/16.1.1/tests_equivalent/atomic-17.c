/* Equiv-rewrite of upstream atomic-17.c: atomic seq_cst == GOMP_atomic (seq_cst default). */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int x = 6;

int
main ()
{
  int v, l = 2, s = 1;
  GOMP_atomic_start (); x = -3 + x; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 3)
    abort ();
  GOMP_atomic_start (); x = 3 * 2 * 1 + x; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 9)
    abort ();
  GOMP_atomic_start (); v = x = x | 16; GOMP_atomic_end ();
  if (v != 25)
    abort ();
  GOMP_atomic_start (); v = x = x + 14 * 2 / 4; GOMP_atomic_end ();
  if (v != 32)
    abort ();
  GOMP_atomic_start (); v = x = 5 | x; GOMP_atomic_end ();
  if (v != 37)
    abort ();
  GOMP_atomic_start (); v = x = 40 + 12 - 2 - 7 - x; GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); { v = x; x = 3 + x; } GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); { v = x; x = -1 * -1 * -1 * -1 - x; } GOMP_atomic_end ();
  if (v != 9)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != -8)
    abort ();
  GOMP_atomic_start (); { x = 2 * 2 - x; v = x; } GOMP_atomic_end ();
  if (v != 12)
    abort ();
  GOMP_atomic_start (); { x = 7 & x; v = x; } GOMP_atomic_end ();
  if (v != 4)
    abort ();
  GOMP_atomic_start (); { v = x; x = 6; } GOMP_atomic_end ();
  if (v != 4)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); { v = x; x = 7 * 8 + 23; } GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 79)
    abort ();
  GOMP_atomic_start (); { v = x; x = 23 + 6 * 4; } GOMP_atomic_end ();
  if (v != 79)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 47)
    abort ();
  GOMP_atomic_start (); { v = x; x = l ? 17 : 12; } GOMP_atomic_end ();
  if (v != 47)
    abort ();
  GOMP_atomic_start (); { v = x; x = l = s++ + 3; } GOMP_atomic_end ();
  if (v != 17 || l != 4 || s != 2)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 4)
    abort ();
  return 0;
}
