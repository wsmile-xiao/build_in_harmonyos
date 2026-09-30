#include <omp.h>
#include <stdlib.h>

int
main ()
{
  int d = omp_get_default_device ();
  int id = omp_get_initial_device ();

  if (d < 0 || d >= omp_get_num_devices ())
    d = id;

  int a[10] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
  int *b = a;
  int shared_mem = 0;
  /* target map(alloc:shared_mem): host fallback -> shared_mem = 1 */
  shared_mem = 1;
  if (omp_target_is_present (b, d) != shared_mem)
    abort ();
  /* target enter data map(to:a): no-op */
  if (omp_target_is_present (b, d) == 0)
    abort ();
  /* target enter data map(alloc:b[:0]): no-op */
  if (omp_target_is_present (b, d) == 0)
    abort ();
  /* target exit data map(release:b[:0]): no-op */
  if (omp_target_is_present (b, d) == 0)
    abort ();
  /* target exit data map(release:b[:0]): no-op */
  if (omp_target_is_present (b, d) != shared_mem)
    abort ();
  /* target enter data map(to:a): no-op */
  if (omp_target_is_present (b, d) == 0)
    abort ();
  /* target enter data map(always,to:b[:0]): no-op */
  if (omp_target_is_present (b, d) == 0)
    abort ();
  /* target exit data map(delete:b[:0]): no-op */
  if (omp_target_is_present (b, d) != shared_mem)
    abort ();
  /* target exit data map(from:b[:0]): no-op */
  return 0;
}
