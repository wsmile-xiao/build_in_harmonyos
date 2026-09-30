/* Equiv-rewrite of upstream pr32468.c.
 * parallel (4 threads) + sections (2 sections): each section sets
 * res[i] = (omp_get_num_threads() != 4). Verifies omp_get_num_threads()
 * returns the team size inside a nested sections construct.
 */
#include <omp.h>
#include <stdlib.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern void GOMP_sections_end (void);

static void
body (void *p)
{
  int *res = (int *) p;
  unsigned s = GOMP_sections_start (2);
  if (s == 1)
    res[0] = (omp_get_num_threads () != 4);
  else if (s == 2)
    res[1] = (omp_get_num_threads () != 4);
  GOMP_sections_end ();
}

int
main (void)
{
  int res[2] = { -1, -1 };
  omp_set_dynamic (0);
  omp_set_num_threads (4);
  GOMP_parallel (body, res, 0, 0);
  if (res[0] != 0 || res[1] != 0)
    abort ();
  return 0;
}
