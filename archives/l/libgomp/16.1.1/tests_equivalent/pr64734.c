/* PR middle-end/64734 - equiv rewrite. target / target data / target update are
 * host-only no-ops; the mapped data already lives in place on host.
 */
#include <stdlib.h>

void
foo (int *x, int *y)
{
  int i;
  for (i = 0; i < 8; i++)
    if (y[i] != 2 + i)
      break;
  if (i != 8 || *x != 1)
    *x = 6;
  else
    {
      *x = 8;
      for (i = 0; i < 8; i++)
	y[i] = 9 + i;
    }
}

int
main (void)
{
  int x = 1, y[8] = { 2, 3, 4, 5, 6, 7, 8, 9 }, i;
  foo (&x, y);
  if (x != 8)
    abort ();
  for (i = 0; i < 8; i++)
    if (y[i] != 9 + i)
      abort ();
  return 0;
}
