/* PR libgomp/35625 - equiv rewrite.
 * "#pragma omp parallel" + "#pragma omp for schedule(guided,10)" empty loops
 * (ascending and descending) -> GOMP_parallel + GOMP_loop_guided.
 */
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_guided_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_guided_next (long *, long *);
extern void GOMP_loop_end (void);

static void
body (void *arg)
{
  (void) arg;
  long istart, iend;
  /* for (int i = 0; i < 1826; i += 10); */
  if (GOMP_loop_guided_start (0, 1826, 10, 10, &istart, &iend))
    {
      do
	{
	}
      while (GOMP_loop_guided_next (&istart, &iend));
    }
  GOMP_loop_end ();
  /* for (int i = 0; i > -1826; i -= 10); */
  if (GOMP_loop_guided_start (0, -1826, -10, 10, &istart, &iend))
    {
      do
	{
	}
      while (GOMP_loop_guided_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  GOMP_parallel (body, 0, 0, 0);
  return 0;
}
