/* Equiv-rewrite of upstream reduction-6.c: parallel for reduction(min:f, max:j). */
#include <omp.h>
#include <stdlib.h>
#include <limits.h>
#include <math.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern int GOMP_loop_static_start (long, long, long, long, long *, long *);
extern int GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 64

struct data
{
  int nt;
  float priv_f[MAXT];
  int priv_j[MAXT];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  int i;
  long istart, iend;
  dd->nt = omp_get_num_threads ();
  dd->priv_f[tn] = INFINITY;
  dd->priv_j[tn] = INT_MIN;

  if (GOMP_loop_static_start (0, 4, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    switch (i)
	      {
	      case 0:
		if (dd->priv_j[tn] < -16) dd->priv_j[tn] = -16; break;
	      case 1:
		if (dd->priv_f[tn] > -2.0) dd->priv_f[tn] = -2.0; break;
	      case 2:
		if (dd->priv_j[tn] < 8) dd->priv_j[tn] = 8;
		if (dd->priv_f[tn] > 9.0) dd->priv_f[tn] = 9.0; break;
	      case 3:
		break;
	      }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

int
main ()
{
  int j;
  float f;
  int t;
  struct data dd;
  j = -10000;
  f = 1024.0;
  GOMP_parallel (body, &dd, 0, 0);

  f = INFINITY;
  j = INT_MIN;
  for (t = 0; t < dd.nt; t++)
    {
      if (dd.priv_f[t] < f) f = dd.priv_f[t];
      if (dd.priv_j[t] > j) j = dd.priv_j[t];
    }
  if (j != 8 || f != -2.0)
    abort ();
  return 0;
}
