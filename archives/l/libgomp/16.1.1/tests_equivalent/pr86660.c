/* PR middle-end/86660 - equiv rewrite. declare target + target map(always,tofrom:v)
 * host-only: v[7]==1, v[5]==3.
 */
#include <stdlib.h>

int v[20];

void
foo (void)
{
  if (v[7] != 2)
    abort ();
  v[7] = 1;
}

int
main (void)
{
  v[5] = 8;
  v[7] = 2;
  foo ();
  v[5] = 3;
  if (v[7] != 1 || v[5] != 3)
    abort ();
  return 0;
}
