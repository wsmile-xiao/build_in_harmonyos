/* alloc-managed-2.c — 完全等价改写 (host-only)
 * 原: #pragma omp target is_device_ptr(a) { ... }  → host 直接执行 body。
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>

int
main ()
{
  int *a = (int *) omp_calloc (5, sizeof (int), ompx_gnu_managed_mem_alloc);
  if (!a)
    abort ();

  for (int i = 0; i < 5; i++)
    if (a[i] != 0)
      abort ();

  a[0] = 42;
  a[4] = 99;
  uintptr_t a_p = (uintptr_t) a;

  /* target is_device_ptr(a) body, host 上直接执行 */
  {
    if (a[0] != 42 || a[4] != 99 || a_p != (uintptr_t) a)
      abort ();
    for (int i = 1; i < 4; i++)
      if (a[i] != 0)
	abort ();
  }

  omp_free (a, ompx_gnu_managed_mem_alloc);
  return 0;
}
