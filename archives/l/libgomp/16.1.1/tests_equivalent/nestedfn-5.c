/* Equiv-rewrite of upstream nestedfn-5.c.
 * GNU nested fn bar() reading i -> static fn (pass i by value, i is read-only).
 * #pragma omp sections -> GOMP_sections_start/end (1-based section numbers).
 * #pragma omp parallel num_threads(2) -> GOMP_parallel.
 * atomic -> GOMP_atomic_start/end.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern void GOMP_sections_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static int bar (int i) { return i + 1; }

static void foo (int *j)
{
  int i = 5;
  unsigned sec = GOMP_sections_start (2);
  if (sec == 1)
    {
      if (bar (i) != 6)
	{ GOMP_atomic_start (); ++*j; GOMP_atomic_end (); }
    }
  else if (sec == 2)
    {
      if (bar (i) != 6)
	{ GOMP_atomic_start (); ++*j; GOMP_atomic_end (); }
    }
  GOMP_sections_end ();
}

static void body (void *p)
{
  foo ((int *) p);
}

int main (void)
{
  int j = 0;
  GOMP_parallel (body, &j, 2, 0);
  if (j)
    abort ();
  return 0;
}
