/* PR middle-end/86416 - equiv rewrite. target map(tofrom:x) host-only: x *= 2.0.
 */
#include <stdlib.h>

long double
foo (long double x)
{
  return x * 2.0L;
}

int
main (void)
{
  long double v = foo (10.0L) - 20.0L;
  if (v > 1.0e-5L || v < -1.0e-5L)
    abort ();
  return 0;
}
