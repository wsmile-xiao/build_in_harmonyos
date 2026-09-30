/* { dg-do run } */

#include <stdbool.h>
#include <stddef.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_loop_static_start (long, long, long, long, long *, long *);
bool GOMP_loop_static_next (long *, long *);
void GOMP_loop_end (void);
bool GOMP_single_start (void);

static int *gp;

static void
parallel_for_body (void *d)
{
  (void) d;
  int i;
  long istart, iend;
  /* target teams distribute parallel for map(p[0:24]) -> host: 1 team,
     parallel loop over [0,24) */
  if (GOMP_loop_static_start (0, 24, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    gp[i] = gp[i] + 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
single_body (void *d)
{
  (void) d;
  if (GOMP_single_start ())
    GOMP_parallel (parallel_for_body, NULL, 0, 0);
}

void
foo (int *p)
{
  gp = p;
  GOMP_parallel (single_body, NULL, 0, 0);
}

int
main ()
{
  int p[24], i;
  for (i = 0; i < 24; i++)
    p[i] = i;
  foo (p);
  for (i = 0; i < 24; i++)
    if (p[i] != i + 1)
      __builtin_abort ();
  return 0;
}
