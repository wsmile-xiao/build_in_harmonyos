/* PR middle-end/35549 - equiv rewrite.
 * Nested "#pragma omp parallel" + atomic + critical -> GOMP_parallel (nested),
 * GOMP_atomic, GOMP_critical.
 */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_critical_start (void);
extern void GOMP_critical_end (void);

struct ctx { int *i; int *n; };

static void
inner_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  if (omp_get_num_threads () != 4)
    {
      GOMP_atomic_start ();
      (*x->n) += 1;
      GOMP_atomic_end ();
    }
  GOMP_critical_start ();
  (*x->i) += 1;
  GOMP_critical_end ();
}

static void
outer_body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  if (omp_get_num_threads () != 3)
    {
      GOMP_atomic_start ();
      (*x->n) += 1;
      GOMP_atomic_end ();
    }
  GOMP_parallel (inner_body, x, 4, 0);
}

int
main (void)
{
  int i = 6, n = 0;
  struct ctx x = { &i, &n };
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_parallel (outer_body, &x, 3, 0);
  if (n == 0 && i != 6 + 3 * 4)
    abort ();
  return 0;
}
