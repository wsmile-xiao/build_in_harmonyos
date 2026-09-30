/* Equiv-rewrite of upstream atomic-10.c: #pragma omp atomic -> GOMP_atomic_start/end. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int x1, x2, x3, x4, x5;
volatile int y6 = 9, y2, y3, y4, y5;
volatile unsigned char z1, z2, z3, z4, z5;
float a1, a2, a3, a4;

void
f1 (void)
{
  GOMP_atomic_start (); x1++; GOMP_atomic_end ();
  GOMP_atomic_start (); x2--; GOMP_atomic_end ();
  GOMP_atomic_start (); ++x3; GOMP_atomic_end ();
  GOMP_atomic_start (); --x4; GOMP_atomic_end ();
  GOMP_atomic_start (); x5 += 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x1 -= y6; GOMP_atomic_end ();
  GOMP_atomic_start (); x2 |= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x3 &= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x4 ^= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); x5 *= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); x1 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); x2 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); x3 <<= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); x4 >>= 3; GOMP_atomic_end ();
}

void
f2 (void)
{
  GOMP_atomic_start (); y6++; GOMP_atomic_end ();
  GOMP_atomic_start (); y2--; GOMP_atomic_end ();
  GOMP_atomic_start (); ++y3; GOMP_atomic_end ();
  GOMP_atomic_start (); --y4; GOMP_atomic_end ();
  GOMP_atomic_start (); y5 += 1; GOMP_atomic_end ();
  GOMP_atomic_start (); y6 -= x1; GOMP_atomic_end ();
  GOMP_atomic_start (); y2 |= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); y3 &= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); y4 ^= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); y5 *= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); y6 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); y2 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); y3 <<= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); y4 >>= 3; GOMP_atomic_end ();
}

void
f3 (void)
{
  GOMP_atomic_start (); z1++; GOMP_atomic_end ();
  GOMP_atomic_start (); z2--; GOMP_atomic_end ();
  GOMP_atomic_start (); ++z3; GOMP_atomic_end ();
  GOMP_atomic_start (); --z4; GOMP_atomic_end ();
  GOMP_atomic_start (); z5 += 1; GOMP_atomic_end ();
  GOMP_atomic_start (); z1 |= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); z2 &= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); z3 ^= 1; GOMP_atomic_end ();
  GOMP_atomic_start (); z4 *= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); z5 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); z1 /= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); z2 <<= 3; GOMP_atomic_end ();
  GOMP_atomic_start (); z3 >>= 3; GOMP_atomic_end ();
}

void
f4 (void)
{
  GOMP_atomic_start (); a1 += 8.0; GOMP_atomic_end ();
  GOMP_atomic_start (); a2 *= 3.5; GOMP_atomic_end ();
  GOMP_atomic_start (); a3 -= a1 + a2; GOMP_atomic_end ();
  GOMP_atomic_start (); a4 /= 2.0; GOMP_atomic_end ();
}

int
main (void)
{
  f1 ();
  if (x1 != -2 || x2 != 0 || x3 != 8 || x4 != -1 || x5 != 3)
    abort ();
  f2 ();
  if (y6 != 4 || y2 != 0 || y3 != 8 || y4 != -1 || y5 != 3)
    abort ();
  f3 ();
  if (z1 != 0 || z2 != 8 || z3 != 0 || z4 != 253 || z5 != 0)
    abort ();
  a1 = 7;
  a2 = 10;
  a3 = 11;
  a4 = 13;
  f4 ();
  if (a1 != 15.0 || a2 != 35.0 || a3 != -39.0 || a4 != 6.5)
    abort ();
  return 0;
}
