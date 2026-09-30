/* Equiv-rewrite of upstream atomic-1.c: #pragma omp atomic -> GOMP_atomic_start/end. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

double d;
struct
{
  int i;
  double e;
  int j;
} x;

void
f1 (void)
{
  GOMP_atomic_start (); d += 7.5; GOMP_atomic_end ();
  GOMP_atomic_start (); d *= 2.5; GOMP_atomic_end ();
  GOMP_atomic_start (); d /= 0.25; GOMP_atomic_end ();
}

void
f2 (void)
{
  GOMP_atomic_start (); x.e += 7.5; GOMP_atomic_end ();
  GOMP_atomic_start (); x.e *= 2.5; GOMP_atomic_end ();
  GOMP_atomic_start (); x.e /= 0.25; GOMP_atomic_end ();
}

int
main (void)
{
  d = 1.0;
  f1 ();
  if (d != 85.0)
    abort ();

  x.e = 1.0;
  f2 ();
  if (x.i != 0 || x.e != 85.0 || x.j != 0)
    abort ();
  return 0;
}
