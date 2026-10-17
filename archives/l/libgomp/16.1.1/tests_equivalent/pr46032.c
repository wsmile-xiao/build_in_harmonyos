/* PR tree-optimization/46032 - equiv rewrite.
 * "#pragma omp parallel for" (each idx independent, no race) -> GOMP_parallel + GOMP_loop_static.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define nEvents 1000

struct ctx { unsigned *results; unsigned *pData; unsigned coeff; };

static void
body (void *arg)
{
  struct ctx *x = (struct ctx *) arg;
  long istart, iend;
  if (GOMP_loop_static_start (0, nEvents, 1, 0, &istart, &iend))
    {
      do
	{
	  long idx;
	  for (idx = istart; idx < iend; idx++)
	    x->results[idx] = x->coeff * x->pData[idx];
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
init (unsigned *results, unsigned *pData)
{
  unsigned i;
  for (i = 0; i < nEvents; ++i)
    pData[i] = i % 3;
}

static void
check (unsigned *results)
{
  unsigned sum = 0;
  int idx;
  for (idx = 0; idx < (int) nEvents; idx++)
    sum += results[idx];
  if (sum != 1998)
    abort ();
}

int
main (void)
{
  unsigned results[nEvents];
  unsigned pData[nEvents];
  unsigned coeff = 2;
  struct ctx x;
  init (results, pData);
  x.results = results;
  x.pData = pData;
  x.coeff = coeff;
  GOMP_parallel (body, &x, 0, 0);
  check (results);
  return 0;
}
