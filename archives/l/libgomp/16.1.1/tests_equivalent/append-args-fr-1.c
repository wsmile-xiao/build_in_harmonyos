/* Minimal equivalent of upstream append-args-fr-1.c.
 *
 * Upstream tests OpenMP 5.1 `#pragma omp declare variant ... append_args(interop(...))`
 * + `#pragma omp dispatch` + `#pragma omp interop use(obj)`, which clang 15
 * cannot lower (no GOMP ABI for these 5.1 device-dispatch features). On OHOS
 * there is no offload device, so the only reachable path is the host path:
 *   check_host(obj): assert (obj == omp_interop_none); check_type(obj)
 *   check_type(obj): for omp_interop_none, every omp_get_interop_type_desc is NULL.
 * We exercise that host interop API directly via omp.h/libgomp.
 */
#include <assert.h>
#include <string.h>
#include <omp.h>

int
main (void)
{
  omp_interop_t obj = omp_interop_none;

  /* check_host */
  assert (obj == omp_interop_none);

  /* check_type: for omp_interop_none all type descriptions are NULL. */
  assert (omp_get_interop_type_desc (obj, omp_ipr_fr_id) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_fr_name) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_vendor) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_vendor_name) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_device_num) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_platform) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_device) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_device_context) == NULL);
  assert (omp_get_interop_type_desc (obj, omp_ipr_targetsync) == NULL);

  /* Host has no offload devices. */
  assert (omp_get_num_devices () == 0);

  return 0;
}
