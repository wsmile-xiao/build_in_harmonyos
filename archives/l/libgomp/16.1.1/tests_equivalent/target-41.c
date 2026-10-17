#include <omp.h>
#include <stdlib.h>

void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);

int v;

static void
foo_body (void *d)
{
  (void) d;
  v++;
}

int
main ()
{
  /* OMP_TARGET_OFFLOAD=mandatory must not fail for explicit host fallback.  */
  /* target if(v): v==0 -> host fallback (-2) */
  if (v)
    GOMP_target (-1, foo_body, NULL, 0, NULL, NULL, NULL);
  else
    GOMP_target (-2, foo_body, NULL, 0, NULL, NULL, NULL);
  /* target device(omp_initial_device): -1 enum remapped to HOST_FALLBACK (-2) */
  GOMP_target (-2, foo_body, NULL, 0, NULL, NULL, NULL);
  /* target device(omp_get_initial_device()): 0 */
  GOMP_target (omp_get_initial_device (), foo_body, NULL, 0, NULL, NULL, NULL);
  omp_set_default_device (omp_get_initial_device ());
  /* target (no device): ICV (-1) -> default device 0 */
  GOMP_target (-1, foo_body, NULL, 0, NULL, NULL, NULL);
  if (v != 4)
    abort ();
  return 0;
}
