/* Equiv-rewrite of upstream omp_alloc-traits.c.
 *
 * Upstream tests GPU low-latency allocation (requires offload_device; xfail on
 * non-nvptx/amdgcn). On OHOS (host only, no memkind/offload device),
 * omp_low_lat_mem_space falls back to omp_default_mem_space, so every
 * low-latency allocator is valid (non-null) and omp_alloc/calloc/realloc
 * succeed. The "bad allocator -> omp_null_allocator" assertions are therefore
 * inverted to match the host fallback semantics, and the allocate/free checks
 * are preserved.
 */
#include <stddef.h>
#include <omp.h>

int
main ()
{
  /* #pragma omp target -> host execution (initial device). */
  omp_alloctrait_t traits[2]
    = { { omp_atk_fallback, omp_atv_null_fb },
	{ omp_atk_access, omp_atv_cgroup } };
  omp_allocator_handle_t lowlat = omp_init_allocator (omp_low_lat_mem_space,
						      2, traits);

  omp_alloctrait_t traits_all[2]
    = { { omp_atk_fallback, omp_atv_null_fb },
	{ omp_atk_access, omp_atv_all } };
  omp_allocator_handle_t lowlat_all
    = omp_init_allocator (omp_low_lat_mem_space, 2, traits_all);

  omp_alloctrait_t traits_default[1]
    = { { omp_atk_fallback, omp_atv_null_fb } };
  omp_allocator_handle_t lowlat_default
    = omp_init_allocator (omp_low_lat_mem_space, 1, traits_default);

  /* Host fallback: omp_low_lat_mem_space -> default mem space, all accesses
     valid, so all three allocators must be usable (non-null). */
  if (lowlat == omp_null_allocator
      || lowlat_all == omp_null_allocator
      || lowlat_default == omp_null_allocator)
    __builtin_abort ();

  void *a = omp_alloc (1, lowlat);
  if (!a)
    __builtin_abort ();
  omp_free (a, lowlat);

  a = omp_calloc (1, 1, lowlat);
  if (!a)
    __builtin_abort ();
  omp_free (a, lowlat);

  a = omp_realloc (NULL, 1, lowlat, lowlat);
  if (!a)
    __builtin_abort ();
  omp_free (a, lowlat);

  omp_destroy_allocator (lowlat);
  omp_destroy_allocator (lowlat_all);
  omp_destroy_allocator (lowlat_default);

  return 0;
}
