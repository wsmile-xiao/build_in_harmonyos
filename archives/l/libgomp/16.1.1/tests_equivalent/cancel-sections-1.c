/* Equiv-rewrite of upstream libgomp.c/cancel-sections-1.c.
 * #pragma omp parallel num_threads(32) { #pragma omp sections { ... #pragma omp cancel sections ... } }
 * manually lowered to GOMP ABI.  Run with OMP_CANCELLATION=true. */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern unsigned GOMP_sections_next (void);
extern void GOMP_sections_end (void);
extern _Bool GOMP_cancel (int, _Bool);

#define GOMP_CANCEL_PARALLEL 1
#define GOMP_CANCEL_LOOP 2
#define GOMP_CANCEL_SECTIONS 4

static void
body (void *data)
{
  (void) data;
  unsigned s = GOMP_sections_start (5);

  while (s != 0)
    {
      if (GOMP_cancel (GOMP_CANCEL_SECTIONS, 1))
	break;			/* cancel sections: leave the section */
      abort ();
      s = GOMP_sections_next ();
    }
  GOMP_sections_end ();
}

int
main (void)
{
  if (!omp_get_cancellation ())
    return 0;
  GOMP_parallel (body, 0, 32, 0);
  return 0;
}
