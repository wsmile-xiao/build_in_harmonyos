/* alloc-managed-3.c — 完全等价改写 (host-only)
 * 原: #pragma omp target is_device_ptr(b) { ... }  → host 直接执行 body。
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>

int
main ()
{
  int *a = (int *) omp_alloc (2 * sizeof (int), ompx_gnu_managed_mem_alloc);
  if (!a)
    abort ();

  a[0] = 42;
  a[1] = 43;

  int *b = (int *) omp_realloc (a, 5 * sizeof (int),
				ompx_gnu_managed_mem_alloc,
				ompx_gnu_managed_mem_alloc);
  if (!b)
    abort ();

  if (b[0] != 42 || b[1] != 43)
    abort ();

  b[2] = 44;
  b[3] = 45;
  b[4] = 46;
  uintptr_t b_p = (uintptr_t) b;

  /* target is_device_ptr(b) body, host 上直接执行 */
  {
    if (b[0] != 42 || b[1] != 43 || b[2] != 44 || b[3] != 45 || b[4] != 46
	|| b_p != (uintptr_t) b)
      abort ();
  }

  omp_free (b, ompx_gnu_managed_mem_alloc);
  return 0;
}
