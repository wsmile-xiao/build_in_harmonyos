/* OMP_TARGET_OFFLOAD=mandatory + OMP_DEFAULT_DEVICE=0 -> host fallback, pass.  */
#include <stdlib.h>

void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);

static int x;

static void
body (void *d)
{
  (void) d;
  x = 5;
}

int
main ()
{
  /* target map(tofrom:x): ICV -> default device 0 (host) */
  GOMP_target (-1, body, NULL, 0, NULL, NULL, NULL);
  if (x != 5)
    __builtin_abort ();
  return 0;
}
