/* Equivalent rewrite: target (host) + 2x "parallel for" -> GOMP_parallel + static loop */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>
#include <stdlib.h>

struct a2_ctx
{
  int **a;
  int n;
  omp_allocator_handle_t alloc;
};

static void
a2_alloc_body (void *vp)
{
  struct a2_ctx *d = (struct a2_ctx *) vp;
  int i;
  long istart, iend;

  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      d->a[i] = omp_alloc (sizeof (int) * 10, d->alloc);
	      d->a[i][0] = i;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
a2_free_body (void *vp)
{
  struct a2_ctx *d = (struct a2_ctx *) vp;
  int i;
  long istart, iend;

  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    omp_free (d->a[i], d->alloc);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
test (int n, omp_allocator_handle_t allocator)
{
  int **a;
  int i;
  struct a2_ctx ctx;

  a = (int **) omp_alloc (n * sizeof (int *), allocator);

  ctx.a = a;
  ctx.n = n;
  ctx.alloc = allocator;

  GOMP_parallel (a2_alloc_body, &ctx, 0, 0);

  for (i = 0; i < n; i++)
    if (a[i][0] != i)
      {
	printf ("data mismatch at %i\n", i);
	abort ();
      }

  GOMP_parallel (a2_free_body, &ctx, 0, 0);

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

  test (1000, omp_default_mem_alloc);
  test (1000, omp_large_cap_mem_alloc);
  test (1000, omp_const_mem_alloc);
  test (1000, omp_high_bw_mem_alloc);
  test (1000, omp_low_lat_mem_alloc);
  test (1000, gpu_lowlat);
  test (1000, omp_cgroup_mem_alloc);
  test (1000, omp_pteam_mem_alloc);
  test (1000, omp_thread_mem_alloc);

  return 0;
}
