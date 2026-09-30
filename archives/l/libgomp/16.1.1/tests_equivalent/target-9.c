#include <stdlib.h>

#define N 123456

int X, Y;

void
foo ()
{
  /* target map(alloc:X): host fallback, data in place */
  X = N;
}

int
main ()
{
  int res;

  foo ();

  /* target map(alloc:X,Y) map(from:res): host fallback */
  {
    Y = N;
    res = X + Y;
  }

  if (res != N + N)
    abort ();

  return 0;
}
