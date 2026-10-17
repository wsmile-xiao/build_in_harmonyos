/* PR libgomp/104952-2 - equiv rewrite. target + simd reduction(&&: result), host-only
 * serial AND reduction; all arr[i] nonzero -> result == 1.
 */
#include <stdlib.h>

#define N 32

static char arr[N];

int
main (void)
{
  unsigned int result = 2;
  unsigned int i;
  for (i = 0; i < N; ++i)
    arr[i] = i + 1;
  for (i = 0; i < N; ++i)
    result = result && arr[i];
  if (result != 1)
    abort ();
  return 0;
}
