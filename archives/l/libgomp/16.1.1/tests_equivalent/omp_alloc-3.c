/* Equivalent rewrite: target (host) + "parallel for" -> GOMP_parallel + static loop */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>
#include <stdlib.h>

#define N 1000

struct a3_ctx
{
  omp_allocator_handle_t alloc;
};

static void
a3_body (void *vp)
{
  struct a3_ctx *d = (struct a3_ctx *) vp;
  int i, j;
  long istart, iend;

  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    for (j = 0; j < N; j++)
	      {
		int *p = omp_alloc (sizeof (int), d->alloc);
		omp_free (p, d->alloc);
	      }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
test (omp_allocator_handle_t allocator)
{
  struct a3_ctx ctx;
  ctx.alloc = allocator;
  GOMP_parallel (a3_body, &ctx, 0, 0);
}

int
main ()
{
  omp_alloctrait_t traits[1] = { { omp_atk_access, omp_atv_cgroup } };
  omp_allocator_handle_t gpu_lowlat;
  gpu_lowlat = omp_init_allocator (omp_low_lat_mem_space, 1, traits);

  test (omp_default_mem_alloc);
  test (omp_large_cap_mem_alloc);
  test (omp_const_mem_alloc);
  test (omp_high_bw_mem_alloc);
  test (omp_low_lat_mem_alloc);
  test (gpu_lowlat);
  test (omp_cgroup_mem_alloc);
  test (omp_pteam_mem_alloc);
  test (omp_thread_mem_alloc);

  return 0;
}
