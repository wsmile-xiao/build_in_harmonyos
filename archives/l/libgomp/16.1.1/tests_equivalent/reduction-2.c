/* Equiv-rewrite of upstream reduction-2.c: parallel + single + for reduction. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern int GOMP_single_start (void);
extern int GOMP_loop_static_start (long, long, long, long, long *, long *);
extern int GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

struct data
{
  int *i, *j, *k;
  double *d;
  int priv_i[4];
  double priv_d[4];
  int priv_k[4];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  int l;
  long istart, iend;

  if (GOMP_single_start ())
    {
      *dd->i = 16;
      *dd->k ^= (1 << 16);
      *dd->d += 32.0;
    }

  dd->priv_i[tn] = 0;
  dd->priv_d[tn] = 1.0;
  dd->priv_k[tn] = ~0;

  if (GOMP_loop_static_start (0, 4, 1, 0, &istart, &iend))
    {
      do
	{
	  for (l = istart; l < iend; l++)
	    {
	      if (omp_get_num_threads () == 4
		  && (dd->priv_i[tn] != 0 || dd->priv_d[tn] != 1.0 || dd->priv_k[tn] != ~0))
		{
		  GOMP_atomic_start (); *dd->j |= 1; GOMP_atomic_end ();
		}
	      if (l == tn)
		{
		  dd->priv_i[tn] = tn;
		  dd->priv_d[tn] = tn + 1;
		  dd->priv_k[tn] = ~(1 << (2 * tn));
		}
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  if (tn == 0)
    {
      int t;
      for (t = 0; t < 4; t++)
	{
	  *dd->i += dd->priv_i[t];
	  *dd->d *= dd->priv_d[t];
	  *dd->k &= dd->priv_k[t];
	}
    }
  GOMP_barrier ();

  if (omp_get_num_threads () == 4)
    {
      if (*dd->i != (16 + 0 + 1 + 2 + 3))
	{
	  GOMP_atomic_start (); *dd->j |= 2; GOMP_atomic_end ();
	}
      if (*dd->d != (33.0 * 1.0 * 2.0 * 3.0 * 4.0))
	{
	  GOMP_atomic_start (); *dd->j |= 4; GOMP_atomic_end ();
	}
      if (*dd->k != (~0 ^ 0x55 ^ (1 << 16)))
	{
	  GOMP_atomic_start (); *dd->j |= 8; GOMP_atomic_end ();
	}
    }
}

int
main (void)
{
  int i = 0, j = 0, k = ~0, l;
  double d = 1.0;
  struct data dd;
  dd.i = &i;
  dd.j = &j;
  dd.k = &k;
  dd.d = &d;
  (void) l;
  GOMP_parallel (body, &dd, 4, 0);
  if (j)
    abort ();
  return 0;
}
