/* PR middle-end/81778 - equiv rewrite. declare target + target simd + target update
 * host-only: write a[BASE..BASE+N-1] = 1.
 */
#include <stdio.h>
#include <stdlib.h>

#define N 32
#define CANARY_SIZE (N * 32)
#define BASE (CANARY_SIZE)
#define ALLOC_SIZE (CANARY_SIZE + N + CANARY_SIZE)

int a[ALLOC_SIZE];

int
main (void)
{
  int s = 1;
  for (int i = N - 1; i > -1; i -= s)
    a[BASE + i] = 1;
  for (int i = 0; i < ALLOC_SIZE; i++)
    {
      int expected = (BASE <= i && i < BASE + N) ? 1 : 0;
      if (a[i] == expected)
	continue;
      printf ("Expected %d, got %d at base[%d]\n", expected, a[i], i - BASE);
      abort ();
    }
  return 0;
}
