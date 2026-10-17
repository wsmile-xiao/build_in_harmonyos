/* Equiv-rewrite of upstream atomic-2.c. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

double d = 1.5;
long double ld = 3;

void
test (void)
{
  GOMP_atomic_start (); d *= 1.25; GOMP_atomic_end ();
  GOMP_atomic_start (); ld /= 0.75; GOMP_atomic_end ();
  if (d != 1.875 || ld != 4.0L)
    abort ();
}

int
main (void)
{
  test ();
  return 0;
}
