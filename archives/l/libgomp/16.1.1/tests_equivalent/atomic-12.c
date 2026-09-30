/* Equiv-rewrite of upstream atomic-12.c: _Bool atomic capture -> GOMP_atomic_start/end. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

_Bool v, x1, x2, x3, x4, x5, x6;

void
foo (void)
{
  GOMP_atomic_start (); v = ++x1; GOMP_atomic_end ();
  if (!v)
    abort ();
  GOMP_atomic_start (); v = x2++; GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); v = --x3; GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); v = x4--; GOMP_atomic_end ();
  if (!v)
    abort ();
  GOMP_atomic_start (); { v = x5; x5 |= 1; } GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); { x6 |= 1; v = x6; } GOMP_atomic_end ();
  if (!v)
    abort ();
}

void
bar (void)
{
  GOMP_atomic_start (); x1 = 0; GOMP_atomic_end ();
  GOMP_atomic_start (); x2 = 0; GOMP_atomic_end ();
  GOMP_atomic_start (); x3 = 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x4 = 1; GOMP_atomic_end ();
  GOMP_atomic_start (); { ++x1; v = x1; } GOMP_atomic_end ();
  if (!v)
    abort ();
  GOMP_atomic_start (); { v = x2; x2++; } GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); { --x3; v = x3; } GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); { v = x4; x4--; } GOMP_atomic_end ();
  if (!v)
    abort ();
  GOMP_atomic_start (); x1 = 0; GOMP_atomic_end ();
  GOMP_atomic_start (); x2 = 0; GOMP_atomic_end ();
  GOMP_atomic_start (); x3 = 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x4 = 1; GOMP_atomic_end ();
  GOMP_atomic_start (); { x1++; v = x1; } GOMP_atomic_end ();
  if (!v)
    abort ();
  GOMP_atomic_start (); { v = x2; ++x2; } GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); { x3--; v = x3; } GOMP_atomic_end ();
  if (v)
    abort ();
  GOMP_atomic_start (); { v = x4; --x4; } GOMP_atomic_end ();
  if (!v)
    abort ();
}

int
main ()
{
  GOMP_atomic_start (); x3 = 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x4 = 1; GOMP_atomic_end ();
  foo ();
  bar ();
  return 0;
}
