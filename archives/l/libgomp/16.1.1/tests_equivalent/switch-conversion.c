/* switch-conversion.c — 完全等价改写 (host-only)
 * 原: #pragma omp declare target foo() + #pragma omp target { n[0]=foo(n[0]); }
 * host 上 declare target 为 no-op，target body 直接执行。
 */
#include <stdlib.h>

static int __attribute__ ((noinline)) foo (int n)
{
  switch (n & 3)
    {
    case 0: return 4;
    case 1: return 3;
    case 2: return 2;
    default:
      return 1;
    }
}

int
main (void)
{
  int n[1];

  n[0] = 4;

  /* target body, host 直接执行 */
  {
    n[0] = foo (n[0]);
  }

  if (n[0] != 4)
    abort ();

  return 0;
}
