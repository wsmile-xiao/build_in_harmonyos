/* Equivalent rewrite: target (host) + "parallel" -> GOMP_parallel; omp_calloc kept as-is */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>
#include <stdlib.h>

struct a5_ctx
{
  int *a;
  int n;
};

static void
a5_body (void *vp)
{
  struct a5_ctx *d = (struct a5_ctx *) vp;
  int i;

  for (i = 0; i < d->n; i++)
    d->a[i] = i;
}

static void
test (int n, omp_allocator_handle_t allocator)
{
  int *a;
  int i;
  struct a5_ctx ctx;

  a = (int *) omp_calloc (n, sizeof (int), allocator);

  for (i = 0; i < n; i++)
    if (a[i] != 0)
      {
	printf ("memory not zeroed at %i\n", i);
	abort ();
      }

  ctx.a = a;
  ctx.n = n;
  GOMP_parallel (a5_body, &ctx, 0, 0);

  for (i = 0; i < n; i++)
    if (a[i] != i)
      {
	printf ("data mismatch at %i\n", i);
	abort ();
      }

  omp_free (a, allocator);
}

int
main ()
{
  omp_alloctrait_t traits[1] = { { omp_atk_access, omp_atv_cgroup } };
  omp_allocator_handle_t gpu_lowlat;
  gpu_lowlat = omp_init_allocator (omp_low_lat_mem_space, 1, traits);

  test (10, omp_default_mem_alloc);
  test (10, omp_large_cap_mem_alloc);
  test (10, omp_const_mem_alloc);
  test (10, omp_high_bw_mem_alloc);
  test (10, omp_low_lat_mem_alloc);
  test (10, gpu_lowlat);
  test (10, omp_cgroup_mem_alloc);
  test (10, omp_pteam_mem_alloc);
  test (10, omp_thread_mem_alloc);

  test (100000, omp_default_mem_alloc);
  test (100000, omp_large_cap_mem_alloc);
  test (100000, omp_const_mem_alloc);
  test (100000, omp_high_bw_mem_alloc);
  test (100000, omp_low_lat_mem_alloc);
  test (100000, gpu_lowlat);
  test (100000, omp_cgroup_mem_alloc);
  test (100000, omp_pteam_mem_alloc);
  test (100000, omp_thread_mem_alloc);

  return 0;
}
