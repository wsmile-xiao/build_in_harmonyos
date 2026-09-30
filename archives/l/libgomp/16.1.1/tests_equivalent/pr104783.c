/* PR libgomp/104783 - equiv rewrite. target + simd + atomic update (host-only):
 * simd is a vectorization hint, single iteration -> val = 1.
 */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int
main (void)
{
  unsigned val = 0;
  for (int i = 0; i < 1; i++)
    {
      GOMP_atomic_start ();
      val = val + 1;
      GOMP_atomic_end ();
    }
  if (val != 1)
    abort ();
  return 0;
}
