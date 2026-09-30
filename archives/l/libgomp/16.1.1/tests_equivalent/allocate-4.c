/* Equiv-rewrite of upstream allocate-4.c.
 * - VLA `int B[n] = {}` (not valid C) -> explicit memset.
 * - #pragma omp allocate(...) -> GOMP_alloc / GOMP_free (GCC lowering).
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "libgomp_g.h"

int
one (void)
{
  int sum = 0;
  omp_allocator_handle_t my_allocator = omp_low_lat_mem_alloc;
  int n = 25;

  /* #pragma omp allocate(A) align(128) allocator(my_allocator) */
  int *A = (int *) GOMP_alloc (128, sizeof (int) * (size_t) n,
			       (uintptr_t) my_allocator);

  if (((intptr_t) A) % 128 != 0)
    abort ();
  for (int i = 0; i < n; ++i)
    A[i] = i;

  omp_alloctrait_t traits[1] = { { omp_atk_alignment, 64 } };
  my_allocator = omp_init_allocator (omp_low_lat_mem_space, 1, traits);
  {
    /* #pragma omp allocate(B,C) allocator(my_allocator) */
    int *B = (int *) GOMP_alloc (64, sizeof (int) * (size_t) n,
				 (uintptr_t) my_allocator);
    memset (B, 0, sizeof (int) * (size_t) n);  /* was `int B[n] = {}` */
    int *C = (int *) GOMP_alloc (64, sizeof (int) * 5,
				 (uintptr_t) my_allocator);
    C[0] = 1; C[1] = 2; C[2] = 3; C[3] = 4; C[4] = 5;

    /* #pragma omp allocate(D) align(256) */
    int *D = (int *) GOMP_alloc (256, sizeof (int) * 5, 0);
    D[0] = 11; D[1] = 22; D[2] = 33; D[3] = 44; D[4] = 55;

    if (((intptr_t) B) % 64 != 0)
      abort ();
    if (((intptr_t) C) % 64 != 0)
      abort ();
    if (((intptr_t) D) % 64 != 0)
      abort ();

    for (int i = 0; i < 5; ++i)
      {
	if (C[i] != i + 1)
	  abort ();
	if (D[i] != i + 1 + 10 * (i + 1))
	  abort ();
      }

    for (int i = 0; i < n; ++i)
      {
	if (B[i] != 0)
	  abort ();
	sum += A[i] + B[i] + C[i % 5] + D[i % 5];
      }

    GOMP_free (B, 0);
    GOMP_free (C, 0);
    GOMP_free (D, 0);
  }
  omp_destroy_allocator (my_allocator);
  GOMP_free (A, 0);
  return sum;
}

int
main (void)
{
  if (one () != 1200)
    abort ();
  return 0;
}
