/* Equiv-rewrite of upstream udr-3.c: user-defined reduction (+:struct S via foo, +:int). */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);

#define MAXT 64

struct S { int s; };

struct data
{
  int nt;
  int priv_s[MAXT];
  int priv_i[MAXT];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  dd->nt = omp_get_num_threads ();

  dd->priv_s[tn] = 0;
  dd->priv_i[tn] = 0;

  if (dd->priv_s[tn] != 0)
    abort ();

  dd->priv_s[tn] = 2;
  dd->priv_i[tn] = 1;
}

int
main ()
{
  struct S s;
  int i = 0;
  int ss, si, k;
  struct data dd;
  s.s = 0;

  GOMP_parallel (body, &dd, 0, 0);

  ss = 0; si = 0;
  for (k = 0; k < dd.nt; k++)
    {
      ss += dd.priv_s[k];
      si += dd.priv_i[k];
    }
  s.s = ss;
  i = si;

  if (s.s != 2 * i)
    abort ();
  return 0;
}
