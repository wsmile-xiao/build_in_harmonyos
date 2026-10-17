/* Equiv-rewrite of upstream atomic-11.c: atomic read/write/update/capture -> GOMP_atomic_start/end. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int x = 6;
float y;

int
main (void)
{
  int v;
  float f;
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 6)
    abort ();
  GOMP_atomic_start (); x = 17; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 17)
    abort ();
  GOMP_atomic_start (); x++; GOMP_atomic_end ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 18)
    abort ();
  GOMP_atomic_start (); v = x++; GOMP_atomic_end ();
  if (v != 18)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 19)
    abort ();
  GOMP_atomic_start (); v = ++x; GOMP_atomic_end ();
  if (v != 20)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 20)
    abort ();
  GOMP_atomic_start (); { v = x; x *= 3; } GOMP_atomic_end ();
  if (v != 20)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 60)
    abort ();
  GOMP_atomic_start ();
  {
    x |= 2;
    v = x;
  }
  GOMP_atomic_end ();
  if (v != 62)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 62)
    abort ();
  GOMP_atomic_start (); { v = x; x++; } GOMP_atomic_end ();
  if (v != 62)
    abort ();
  GOMP_atomic_start (); { v = x; ++x; } GOMP_atomic_end ();
  if (v != 63)
    abort ();
  GOMP_atomic_start ();
  {
    ++x;
    v = x;
  }
  GOMP_atomic_end ();
  if (v != 65)
    abort ();
  GOMP_atomic_start (); { x++; v = x; } GOMP_atomic_end ();
  if (v != 66)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 66)
    abort ();
  GOMP_atomic_start (); { v = x; x--; } GOMP_atomic_end ();
  if (v != 66)
    abort ();
  GOMP_atomic_start (); { v = x; --x; } GOMP_atomic_end ();
  if (v != 65)
    abort ();
  GOMP_atomic_start ();
  {
    --x;
    v = x;
  }
  GOMP_atomic_end ();
  if (v != 63)
    abort ();
  GOMP_atomic_start (); { x--; v = x; } GOMP_atomic_end ();
  if (v != 62)
    abort ();
  GOMP_atomic_start (); v = x; GOMP_atomic_end ();
  if (v != 62)
    abort ();
  GOMP_atomic_start (); y = 17.5f; GOMP_atomic_end ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (f != 17.5)
    abort ();
  GOMP_atomic_start (); y *= 2.0f; GOMP_atomic_end ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (y != 35.0)
    abort ();
  GOMP_atomic_start (); f = y *= 2.0f; GOMP_atomic_end ();
  if (f != 70.0)
    abort ();
  GOMP_atomic_start (); f = y++; GOMP_atomic_end ();
  if (f != 70.0)
    abort ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (f != 71.0)
    abort ();
  GOMP_atomic_start (); f = --y; GOMP_atomic_end ();
  if (f != 70.0)
    abort ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (f != 70.0)
    abort ();
  GOMP_atomic_start (); { f = y; y /= 2.0f; } GOMP_atomic_end ();
  if (f != 70.0)
    abort ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (f != 35.0)
    abort ();
  GOMP_atomic_start (); { y /= 2.0f; f = y; } GOMP_atomic_end ();
  if (f != 17.5)
    abort ();
  GOMP_atomic_start (); f = y; GOMP_atomic_end ();
  if (f != 17.5)
    abort ();
  return 0;
}
