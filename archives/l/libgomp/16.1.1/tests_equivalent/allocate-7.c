/* Equiv-rewrite of upstream allocate-7.c.
 * - [[omp::decl(allocate,allocator(...),align(...))]] -> __attribute__((aligned(...)))
 * - _Alignof(expr) (GNU extension) -> _Alignof(type)
 * - #pragma omp allocate(A1,B1) align(512) allocator(...) -> GOMP_alloc/GOMP_free.
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>
#include "libgomp_g.h"

int AAA __attribute__ ((aligned (4096)));

_Static_assert (_Alignof (int) == _Alignof (int), "wrong alignment");

static void
test0 (void)
{
  /* #pragma omp allocate(A1, B1) align(512) allocator(omp_default_mem_alloc) */
  int *A1 = (int *) GOMP_alloc (512, sizeof (int) * 5,
				(uintptr_t) omp_default_mem_alloc);
  int *B1 = (int *) GOMP_alloc (512, sizeof (int),
				(uintptr_t) omp_default_mem_alloc);

  _Static_assert (_Alignof (int[5]) == _Alignof (int[5]), "wrong alignment");
  _Static_assert (_Alignof (int) == _Alignof (int), "wrong alignment");

  if ((((uintptr_t) A1) % 512) != 0)
    abort ();
  if ((((uintptr_t) B1) % 512) != 0)
    abort ();

  GOMP_free (A1, 0);
  GOMP_free (B1, 0);
}

int
main (void)
{
  static int BBB __attribute__ ((aligned (4096)));

  _Static_assert (_Alignof (int) == _Alignof (int), "wrong alignment");

  if ((((uintptr_t) &AAA) % 4096) != 0)
    abort ();
  if ((((uintptr_t) &BBB) % 4096) != 0)
    abort ();

  test0 ();

  return 0;
}
