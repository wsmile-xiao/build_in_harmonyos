/* PR target/90811 - equiv rewrite. target teams distribute parallel for simd
 * (host-only) -> GOMP_parallel + GOMP_loop_static over 100 independent iterations.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

long long a[100], b[100];

static void
body (void *arg)
{
  (void) arg;
  long ist, ien;
  if (GOMP_loop_static_start (0, 100, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    {
	      long long c = 0;
	      const long long d[] = { 1, 3, 5, 7, 9 };
	      for (int j = 4; j >= 0; j--)
		c = d[j] + b[i] * c;
	      a[i] += c;
	    }
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  int i;
  for (i = 0; i < 100; i++)
    {
      a[i] = i;
      b[i] = i % 10;
    }
  GOMP_parallel (body, 0, 0, 0);
  for (i = 0; i < 100; i++)
    {
      const long long r[] = { 1, 26, 229, 976, 2849, 6646, 13381, 24284, 40801, 64594 };
      if (a[i] != r[i % 10] + (i / 10 * 10))
	abort ();
    }
  return 0;
}
