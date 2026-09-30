#include <omp.h>
#include <stdlib.h>

int
main ()
{
  if (omp_get_level ())
    abort ();
  /* target if(0) -> host fallback (serial), no offload */
  if (omp_get_level ())
    abort ();
  /* target if(0) + teams + distribute -> host: 1 team, serial loop */
  for (int i = 0; i < 1; ++i)
    if (omp_get_level ())
      abort ();
  return 0;
}
