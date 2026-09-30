#include <omp.h>
#include <stdlib.h>
#include <stdbool.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);
bool GOMP_single_start (void);

static int check_fail;

static void
target_if0_body (void *d)
{
  (void) d;
  /* #pragma omp single inside target if(0): single thread runs the check */
  if (GOMP_single_start ())
    if (omp_get_num_threads () != 1)
      check_fail = 1;
}

static void
parallel_body (void *d)
{
  (void) d;
  /* target if(0): host fallback, serialized region -> num_threads == 1 */
  GOMP_target (omp_get_initial_device (), target_if0_body, NULL, 0, NULL, NULL, NULL);
}

int
main ()
{
  omp_set_dynamic (0);
  check_fail = 0;
  GOMP_parallel (parallel_body, NULL, 4, 0);
  if (check_fail)
    abort ();
  return 0;
}
