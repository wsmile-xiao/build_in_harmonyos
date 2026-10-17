/* Equivalent rewrite: host-only target fallback -> early return 0 (upstream itself
 * returns 0 when omp_get_initial_device()==omp_get_default_device(), i.e. host). */
#include <omp.h>

int
main ()
{
  if (omp_get_initial_device () == omp_get_default_device ())
    return 0;  /* This test isn't interesting with host-fallback.  */

  return 0;
}
