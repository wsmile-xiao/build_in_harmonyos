/* Equiv-rewrite of upstream udr-2.c: user-defined reductions (+:S, foo:S, foo:int). */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);

#define MAXT 64

struct S { int s; };

struct data
{
  int nt;
  int priv_s[MAXT];
  int priv_q[MAXT];
  int priv_t[MAXT];
  int priv_u[MAXT];
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int tn = omp_get_thread_num ();
  dd->nt = omp_get_num_threads ();

  dd->priv_s[tn] = 0;
  dd->priv_q[tn] = 0;
  dd->priv_t[tn] = 0;
  dd->priv_u[tn] = 0;

  if (dd->priv_s[tn] != 0 || dd->priv_t[tn] != 0 || dd->priv_u[tn] != 0 || dd->priv_q[tn] != 0)
    abort ();

  dd->priv_s[tn] = 6;
  dd->priv_t[tn] = 8;
  dd->priv_u[tn] = 9;
  dd->priv_q[tn]++;
}

int
main ()
{
  int u = 0, q = 0;
  struct S s, t;
  int ss, st, su, sq, k;
  struct data dd;
  s.s = 0; t.s = 0;

  GOMP_parallel (body, &dd, 0, 0);

  ss = 0; st = 0; su = 0; sq = 0;
  for (k = 0; k < dd.nt; k++)
    {
      ss += dd.priv_s[k];
      st += dd.priv_t[k];
      su += dd.priv_u[k];
      sq += dd.priv_q[k];
    }
  s.s = ss;
  t.s = st;
  u = su;
  q = sq;

  if (s.s != 6 * q || t.s != 8 * q || u != 9 * q)
    abort ();
  return 0;
}
