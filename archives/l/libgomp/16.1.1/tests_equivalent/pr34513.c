/* Equiv-rewrite of upstream pr34513.c.
 * parallel num_threads(4) with a function-local static `shrd` (shared), an
 * atomic increment, a barrier, then a check that shrd == 4.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static int errors = 0;
static int thrs = 4;
static int shrd = 0;   /* was function-local static; same shared storage */

static void
body (void *p)
{
  (void) p;
  GOMP_atomic_start (); shrd += 1; GOMP_atomic_end ();
  GOMP_barrier ();
  if (shrd != thrs)
    { GOMP_atomic_start (); errors += 1; GOMP_atomic_end (); }
}

int
main (void)
{
  omp_set_dynamic (0);
  GOMP_parallel (body, 0, thrs, 0);
  if (errors)
    abort ();
  return 0;
}
