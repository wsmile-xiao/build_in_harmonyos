/* OMP_TARGET_OFFLOAD=default -> host fallback, pass.  */
#include <omp.h>
#include <stdlib.h>

void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);

static int x;

static void
body (void *d)
{
  (void) d;
  x = 5 + omp_is_initial_device ();
}

int
main ()
{
  GOMP_target (-1, body, NULL, 0, NULL, NULL, NULL);

  if (x != 5 + (omp_get_default_device () == omp_get_initial_device ()))
    __builtin_abort ();

  return 0;
}
