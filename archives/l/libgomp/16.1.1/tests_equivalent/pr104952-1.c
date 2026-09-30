/* PR libgomp/104952-1 - equiv rewrite. target + simd reduction(||: result), host-only
 * serial OR reduction; arr[5]==42 -> result == 1.
 */
#include <stdlib.h>

#define N 32

static char arr[N];

int
main (void)
{
  unsigned int result = 0;
  unsigned int i;
  for (i = 0; i < N; ++i)
    arr[i] = 0;
  arr[5] = 42;
  for (i = 0; i < N; ++i)
    result = result || arr[i];
  if (result != 1)
    abort ();
  return 0;
}
