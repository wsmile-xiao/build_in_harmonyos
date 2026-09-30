/* PR middle-end/90779 - equiv rewrite. target map(from:j) host-only: static k
 * increments twice -> j == 7.
 */
#include <stdlib.h>

int
main (void)
{
  int i, j;
  for (i = 0; i < 2; ++i)
    {
      static int k = 5;
      j = ++k;
    }
  if (j != 7)
    abort ();
  return 0;
}
