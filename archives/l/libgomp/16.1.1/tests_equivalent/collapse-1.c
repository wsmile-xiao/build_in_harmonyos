/* Equiv-rewrite of upstream libgomp.c/collapse-1.c.
 * "parallel for collapse(3)" and "parallel { for collapse(2) reduction(|:l) }"
 * lowered to GOMP ABI (collapse linearized, GOMP_loop_static_start). */
#include <string.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static int a[3][3][3];

/* collapse(3) over i,j,k in [0,2): linear index = i*4 + j*2 + k. */
static void
fill (void *data)
{
  (void) data;
  long istart, iend, idx;

  if (GOMP_loop_static_start (0, 8, 1, 4, &istart, &iend))
    {
      do
	{
	  for (idx = istart; idx < iend; idx++)
	    {
	      int i = idx / 4;
	      int j = (idx / 2) % 2;
	      int k = idx % 2;
	      a[i][j][k] = i + j * 4 + k * 16;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

/* collapse(2) over i,j in [0,2): linear index = i*2 + j; k is a private
 * inner loop; reduction(|:l). */
static void
check (void *data)
{
  int *lp = data;
  int myl = 0;
  long istart, iend, idx;
  int k;

  if (GOMP_loop_static_start (0, 4, 1, 1, &istart, &iend))
    {
      do
	{
	  for (idx = istart; idx < iend; idx++)
	    {
	      int i = idx / 2;
	      int j = idx % 2;
	      for (k = 0; k < 2; k++)
		if (a[i][j][k] != i + j * 4 + k * 16)
		  myl = 1;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  GOMP_atomic_start ();
  *lp |= myl;
  GOMP_atomic_end ();
}

int
main (void)
{
  int l = 0;

  memset (a, '\0', sizeof (a));
  GOMP_parallel (fill, 0, 0, 0);
  GOMP_parallel (check, &l, 0, 0);

  if (l)
    abort ();
  return 0;
}
