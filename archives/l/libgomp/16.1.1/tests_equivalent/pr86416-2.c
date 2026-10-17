/* Equiv-rewrite of upstream pr86416-2.c.
 * - __float128 -> long double, Q literal -> L.
 * - #pragma omp target map(tofrom:y) -> host execution (no offload device).
 */
#include <stdlib.h>

long double
foo (long double y)
{
  /* omp target map(tofrom:y) on host == direct execution of the body. */
  y *= 4.0L;
  return y;
}

int
main (void)
{
  long double v = foo (5.0L) - 20.0L;
  if (v > 1.0e-5L || v < -1.0e-5L)
    abort ();
  return 0;
}
