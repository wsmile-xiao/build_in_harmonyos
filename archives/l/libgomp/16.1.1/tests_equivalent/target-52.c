/* Equiv-rewrite of upstream target-52.c (upstream gate: { target offload_device }).
 *
 * target-52.c checks offload-device behavior: on a non-host device
 * omp_is_initial_device()==0 inside the target region (=> x == 5) and the
 * default device is 0.
 *
 * On a host-only device (no offload target), #pragma omp target runs via host
 * fallback, so omp_is_initial_device()==1 inside the region (=> x == 5+1) and
 * the default device equals omp_get_initial_device() (== omp_get_num_devices()
 * == 0).  This is exactly the host-only counterpart upstream encodes in
 * target-53.c.  The region is lowered to GOMP_target.
 */
#include <omp.h>
#include <stddef.h>

extern void GOMP_target (int, void (*) (void *), const void *, size_t,
			 void **, size_t *, unsigned char *);

static void
body (void *p)
{
  int *x = ((void **) p)[0];
  *x = 5 + omp_is_initial_device ();
}

int
main (void)
{
  int x;
  void *ha[1] = { &x };
  size_t sz[1] = { sizeof x };
  unsigned char kk[1] = { 3 };	/* GOMP_MAP_TOFROM */
  GOMP_target (0, body, NULL, 1, ha, sz, kk);

  if (x != 5 + 1)
    __builtin_abort ();
  if (omp_get_default_device () != omp_get_initial_device ())
    __builtin_abort ();
  return 0;
}
