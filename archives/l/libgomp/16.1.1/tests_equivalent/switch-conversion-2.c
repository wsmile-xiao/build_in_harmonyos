/* switch-conversion-2.c — 完全等价改写 (host-only)
 * 原: #pragma omp target { ... } → host 直接执行 body。
 */
#include <stdlib.h>

int
main (void)
{
  int n[1];

  n[0] = 3;

  /* target body, host 直接执行 */
  {
    int m = n[0];
    switch (m & 3)
      {
      case 0: m = 4; break;
      case 1: m = 3; break;
      case 2: m = 2; break;
      default:
	m = 1; break;
      }
    n[0] = m;
  }

  if (n[0] != 1)
    abort ();

  return 0;
}
