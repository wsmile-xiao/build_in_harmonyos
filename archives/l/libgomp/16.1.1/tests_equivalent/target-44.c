#include <stdlib.h>

struct s
{
  int i;
};

int
main (void)
{
  const int N0 = 32768;

  struct s counter_N0 = { 0 };
  /* target + for simd reduction(+:counter_N0): host fallback, serial */
  for (int i0 = 0 ; i0 < N0 ; i0++ )
    counter_N0.i += 1;

  if (counter_N0.i != N0)
    abort ();

  return 0;
}
