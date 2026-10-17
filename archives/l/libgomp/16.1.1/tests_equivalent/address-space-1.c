/* Equiv-rewrite of upstream address-space-1.c.
 * - __seg_fs (x86 FS segment) -> plain global variable.
 * - #pragma omp target map(alloc:a) map(from:b) -> host execution.
 */
#include <assert.h>

int a;

int
main (void)
{
  int b;
  /* omp target map(alloc:a) map(from:b) on host == direct execution. */
  a = 321;
  asm volatile ("" : : "g" (&a) : "memory");
  b = a;
  assert (b == 321);
  return 0;
}
