/* single-2.c — 完全等价改写
 * 原: #pragma omp single copyprivate(i) { i=6; } 位于 main 顶层(无 parallel)，
 * 因此单线程执行，copyprivate 无广播对象，等价于 GOMP_single_start 后直接赋值。
 */
#include <stdlib.h>
#include <stdbool.h>

extern bool GOMP_single_start (void);

int
main (void)
{
  int i;
  i = 4;
  if (GOMP_single_start ())
    {
      i = 6;
    }
  if (i != 6)
    abort ();
  return 0;
}
