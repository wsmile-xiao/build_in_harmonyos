/* Equiv-rewrite of upstream reduction-1.c: parallel reduction (+, *, &) -> per-thread copies. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

struct data
{
  int *j;
  int priv_i[4];
  double priv_d[4];
  int priv_k[4];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  dd->priv_i[tn] = 0;
  dd->priv_d[tn] = 1.0;
  dd->priv_k[tn] = ~0;

  if (dd->priv_i[tn] != 0 || dd->priv_d[tn] != 1.0 || dd->priv_k[tn] != ~0)
    {
      GOMP_atomic_start (); *dd->j |= 1; GOMP_atomic_end ();
    }
  if (omp_get_num_threads () != 4)
    {
      GOMP_atomic_start (); *dd->j |= 2; GOMP_atomic_end ();
    }

  dd->priv_i[tn] = omp_get_thread_num ();
  dd->priv_d[tn] = dd->priv_i[tn] + 1;
  dd->priv_k[tn] = ~(1 << (2 * dd->priv_i[tn]));
}

int
main (void)
{
  int i = 0, j = 0, k = ~0;
  double d = 1.0;
  struct data dd;
  dd.j = &j;
  GOMP_parallel (body, &dd, 4, 0);

  if (j & 1)
    abort ();
  if ((j & 2) == 0)
    {
      i = dd.priv_i[0] + dd.priv_i[1] + dd.priv_i[2] + dd.priv_i[3];
      d = dd.priv_d[0] * dd.priv_d[1] * dd.priv_d[2] * dd.priv_d[3];
      k = dd.priv_k[0] & dd.priv_k[1] & dd.priv_k[2] & dd.priv_k[3];
      if (i != (0 + 1 + 2 + 3))
	abort ();
      if (d != (1.0 * 2.0 * 3.0 * 4.0))
	abort ();
      if (k != (~0 ^ 0x55))
	abort ();
    }
  return 0;
}
