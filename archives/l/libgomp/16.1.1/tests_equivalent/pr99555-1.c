/* PR99555 - equiv rewrite. target parallel task (empty bodies) -> GOMP_parallel + GOMP_task.
 */
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

static void
empty_body (void *arg)
{
  (void) arg;
}

static void
par_body (void *arg)
{
  (void) arg;
  GOMP_task (empty_body, 0, 0, 0, 0, 1, 0, 0, 0, 0);
}

int
main (void)
{
  GOMP_parallel (par_body, 0, 0, 0);
  return 0;
}
