#include <omp.h>
#include <stdlib.h>

volatile int v;

void
foo (int f)
{
  int d = f ? omp_get_num_devices () : omp_get_default_device ();
  int h = 5;
  /* All target/target-data/target-update regions run on the host
     (no offload device): data stays in place, omp_is_initial_device()
     returns true, omp_get_level() stays 0.  */
  if (omp_get_level () != 0)
    abort ();
  if (omp_get_level () != 0 || !omp_is_initial_device ())
    abort ();
  if (omp_get_level () != 0 || !omp_is_initial_device ())
    abort ();
  if (omp_get_level () != 0)
    abort ();
  if (omp_get_level () != 0 || (f && !omp_is_initial_device ()))
    abort ();
  if (omp_get_level () != 0 || !omp_is_initial_device ())
    abort ();
  if (omp_get_level () != 0 || !omp_is_initial_device ())
    abort ();
  if (omp_get_level () != 0)
    abort ();
  if (omp_get_level () != 0 || (f && !omp_is_initial_device ()))
    abort ();
  {
    if (omp_get_level () != 0 || (f && !omp_is_initial_device ()) || h++ != 5)
      abort ();
  }
  {
    if (omp_get_level () != 0 || !omp_is_initial_device () || h++ != 6)
      abort ();
  }
  {
    if (omp_get_level () != 0 || !omp_is_initial_device () || h++ != 7)
      abort ();
  }
  {
    if (omp_get_level () != 0 || h++ != 8)
      abort ();
  }
  {
    if (omp_get_level () != 0 || (f && !omp_is_initial_device ()) || h++ != 9)
      abort ();
  }
  {
    if (omp_get_level () != 0 || !omp_is_initial_device () || h++ != 10)
      abort ();
  }
  {
    if (omp_get_level () != 0 || !omp_is_initial_device () || h++ != 11)
      abort ();
  }
  {
    if (omp_get_level () != 0 || h++ != 12)
      abort ();
  }
  {
    if (omp_get_level () != 0 || (f && !omp_is_initial_device ()) || h++ != 13)
      abort ();
  }
  if (h != 14)
    abort ();
}

int
main ()
{
  foo (0);
  foo (1);
  return 0;
}
