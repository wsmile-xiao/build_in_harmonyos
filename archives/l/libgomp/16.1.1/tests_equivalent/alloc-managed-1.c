/* alloc-managed-1.c — 完全等价改写 (host-only)
 * 原: #pragma omp target is_device_ptr(a) { ... }  → host 直接执行 body。
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>

int
main ()
{
  int *a = (int *) omp_alloc (sizeof (int), ompx_gnu_managed_mem_alloc);
  if (!a)
    abort ();

  *a = 42;
  uintptr_t a_p = (uintptr_t) a;

  /* target is_device_ptr(a) body, host 上直接执行 */
  {
    if (*a != 42 || a_p != (uintptr_t) a)
      abort ();
  }

  omp_free (a, ompx_gnu_managed_mem_alloc);
  return 0;
}
