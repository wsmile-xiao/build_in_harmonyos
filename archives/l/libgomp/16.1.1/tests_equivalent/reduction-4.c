/* Equiv-rewrite of upstream reduction-4.c: reduction(-:|:^).  NOTE: GCC's
 * reduction(-:i) (deprecated, PR libgomp/38935) behaves like reduction(+:i),
 * producing the positive sum 0+1+2+3; the upstream assertion expects exactly
 * that, so the "-" combine is implemented as addition here. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

struct data
{
  int *j;
  int priv_i[4];
  int priv_k[4];
  int priv_l[4];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  dd->priv_i[tn] = 0;
  dd->priv_k[tn] = 0;
  dd->priv_l[tn] = 0;

  if (dd->priv_i[tn] != 0 || dd->priv_k[tn] != 0 || dd->priv_l[tn] != 0)
    {
      GOMP_atomic_start (); *dd->j |= 1; GOMP_atomic_end ();
    }
  if (omp_get_num_threads () != 4)
    {
      GOMP_atomic_start (); *dd->j |= 2; GOMP_atomic_end ();
    }

  dd->priv_i[tn] = omp_get_thread_num ();
  dd->priv_k[tn] = 1 << (2 * dd->priv_i[tn]);
  dd->priv_l[tn] = 0xea << (3 * dd->priv_i[tn]);
}

int
main (void)
{
  int i = 0, j = 0, k = 0, l = 0;
  struct data dd;
  dd.j = &j;
  GOMP_parallel (body, &dd, 4, 0);

  if (j & 1)
    abort ();
  if ((j & 2) == 0)
    {
      i = dd.priv_i[0] + dd.priv_i[1] + dd.priv_i[2] + dd.priv_i[3];
      k = dd.priv_k[0] | dd.priv_k[1] | dd.priv_k[2] | dd.priv_k[3];
      l = dd.priv_l[0] ^ dd.priv_l[1] ^ dd.priv_l[2] ^ dd.priv_l[3];
      if (i != (0 + 1 + 2 + 3))
	abort ();
      if (k != 0x55)
	abort ();
      if (l != 0x1e93a)
	abort ();
    }
  return 0;
}
