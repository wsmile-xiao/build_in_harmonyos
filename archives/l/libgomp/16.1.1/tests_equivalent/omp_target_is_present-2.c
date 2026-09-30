/* Equiv-rewrite of upstream omp_target_is_present-2.c (REQ_SELF_MAPS=1 +
 * #pragma omp requires self_maps).  On host-only, initial_dev is always true
 * for non-invalid device numbers, so self_mapping stays false and the target
 * pragmas are unreachable no-ops; the pure API assertions remain unchanged.
 */
#include <omp.h>
#include <stdbool.h>
#include <stddef.h>

#ifndef REQ_SELF_MAPS
#define REQ_SELF_MAPS 1
#endif

int gEnter = 3, gLink = 4, gLocal = 5;

static void
check_routines (int dev)
{
  int A = 1, B = 2;

  int dev2 = dev;
  if (dev2 == omp_default_device)
    dev2 = omp_get_default_device ();

  bool initial_dev = dev2 == omp_initial_device || dev2 == omp_get_num_devices ();
  bool self_mapping = false;
  bool invalid_dev = dev == omp_invalid_device;
  /* (host-only: !invalid_dev && !initial_dev is never true) */

  if (omp_target_is_present (NULL, dev) != 0)
    __builtin_abort ();

  if (omp_target_is_accessible (NULL, 0, dev) != 0)
    __builtin_abort ();

  if (invalid_dev)
    return;

  if (omp_target_is_present (&A, dev) != initial_dev)
    __builtin_abort ();

  if (omp_target_is_present (&gEnter, dev) != !invalid_dev)
    __builtin_abort ();

  if (omp_target_is_present (&gLink, dev) != (!invalid_dev && (initial_dev || !REQ_SELF_MAPS)))
    __builtin_abort ();

  if (omp_target_is_present (&gLocal, dev) != !invalid_dev)
    __builtin_abort ();

  int *ptr = (int *) 0xDEEDBEEF;
  if (!invalid_dev)
    {
      ptr = omp_target_alloc (sizeof (int), dev);
      if (ptr == NULL || !omp_target_is_accessible (ptr, sizeof (int), dev))
	__builtin_abort ();
    }

  if ((initial_dev || invalid_dev) && omp_target_associate_ptr (ptr, ptr, sizeof (int), 0, dev) == 0)
    __builtin_abort ();
  if ((initial_dev || invalid_dev) && omp_target_associate_ptr (((char *) ptr) + 2, ptr, sizeof (int) - 2, 2, dev) == 0)
    __builtin_abort ();

  if (!!omp_target_associate_ptr (&B, ptr, sizeof (int), 0, dev)
      != (self_mapping || initial_dev || invalid_dev))
    __builtin_abort ();

  if (!!omp_target_associate_ptr (&B, ptr, sizeof (int), 0, dev)
      != (self_mapping || initial_dev || invalid_dev))
    __builtin_abort ();

  if (!!omp_target_is_present (&A, dev)
      != (initial_dev || (!self_mapping && !invalid_dev)))
    __builtin_abort ();

  if (!!omp_target_is_present (&B, dev)
      != (initial_dev || (!self_mapping && !invalid_dev)))
    __builtin_abort ();

  if (!!omp_target_is_present (&gEnter, dev)
      != (initial_dev || (!invalid_dev)))
    __builtin_abort ();

  if (!!omp_target_is_present (&gLink, dev)
      != (initial_dev || (!self_mapping && !invalid_dev)))
    __builtin_abort ();

  if (!!omp_target_is_present (&gLocal, dev) != !invalid_dev)
    __builtin_abort ();

  int *ptr2 = omp_get_mapped_ptr (&A, dev);
  if (initial_dev)
    {
      if (ptr2 != &A)
	__builtin_abort ();
    }
  else if (invalid_dev || self_mapping)
    {
      if (ptr2 != NULL)
	__builtin_abort ();
    }
  else if (ptr2 == &A || ptr2 == NULL)
    __builtin_abort ();

  ptr2 = omp_get_mapped_ptr (&B, dev);
  if (initial_dev)
    {
      if (ptr2 != &B)
	__builtin_abort ();
    }
  else if (invalid_dev || self_mapping)
    {
      if (ptr2 != NULL)
	__builtin_abort ();
    }
  else if (ptr2 != ptr)
    __builtin_abort ();

  ptr2 = omp_get_mapped_ptr (&gEnter, dev);
  if (initial_dev)
    {
      if (ptr2 != &gEnter)
	__builtin_abort ();
    }
  else if (invalid_dev)
    {
      if (ptr2 != NULL)
	__builtin_abort ();
    }
  else if (ptr2 == &gEnter || ptr2 == NULL)
    __builtin_abort ();

  ptr2 = omp_get_mapped_ptr (&gLink, dev);
  if (initial_dev)
    {
      if (ptr2 != &gLink)
	__builtin_abort ();
    }
  else if (invalid_dev || self_mapping)
    {
      if (ptr2 != NULL)
	__builtin_abort ();
    }
  else if (ptr2 == ptr || ptr2 == NULL)
    __builtin_abort ();

  ptr2 = omp_get_mapped_ptr (&gLocal, dev);
  if (initial_dev)
    {
      if (ptr2 != &gLocal)
	__builtin_abort ();
    }
  else if (invalid_dev)
    {
      if (ptr2 != NULL)
	__builtin_abort ();
    }
  else if (ptr2 == &gLocal || ptr2 == NULL)
    __builtin_abort ();

  if (!!omp_target_disassociate_ptr (&B, dev)
      != (self_mapping || initial_dev || invalid_dev))
    __builtin_abort ();
  if (!invalid_dev)
    {
      omp_target_free (ptr, dev);
    }
}

int
main (void)
{
  for (int dev = omp_initial_device; dev <= omp_get_num_devices (); dev++)
    check_routines (dev);

  check_routines (omp_invalid_device);
  check_routines (omp_default_device);

  for (int dev = omp_initial_device; dev <= omp_get_num_devices (); dev++)
    {
      omp_set_default_device (dev);
      check_routines (omp_default_device);
    }
}
