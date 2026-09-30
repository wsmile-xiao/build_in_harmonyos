/* Equiv-rewrite of upstream reduction-5.c: parallel/sections reduction(+:sum,*:prod). */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern unsigned GOMP_sections_next (void);
extern void GOMP_sections_end (void);

#define MAXT 64

struct dsum
{
  int nt;
  int priv[MAXT];
};

struct dsp
{
  int nt;
  int priv_s[MAXT];
  int priv_p[MAXT];
};

static void
body_sum (void *p)
{
  struct dsum *d = (struct dsum *) p;
  int tn = omp_get_thread_num ();
  unsigned sn;
  d->nt = omp_get_num_threads ();
  d->priv[tn] = 0;
  sn = GOMP_sections_start (3);
  while (sn)
    {
      d->priv[tn] += 2;
      sn = GOMP_sections_next ();
    }
  GOMP_sections_end ();
}

static void
body_sumprod (void *p)
{
  struct dsp *d = (struct dsp *) p;
  int tn = omp_get_thread_num ();
  unsigned sn;
  d->nt = omp_get_num_threads ();
  d->priv_s[tn] = 0;
  d->priv_p[tn] = 1;
  sn = GOMP_sections_start (3);
  while (sn)
    {
      d->priv_s[tn] += 2;
      d->priv_p[tn] *= 2;
      sn = GOMP_sections_next ();
    }
  GOMP_sections_end ();
}

int
main (void)
{
  int sum = 0, prod = 1;
  int t;
  struct dsum ds;
  struct dsp dsp;

  GOMP_parallel (body_sum, &ds, 0, 0);
  sum = 0;
  for (t = 0; t < ds.nt; t++)
    sum += ds.priv[t];
  if (sum != 6)
    abort ();

  sum = 0;
  GOMP_parallel (body_sum, &ds, 0, 0);
  sum = 0;
  for (t = 0; t < ds.nt; t++)
    sum += ds.priv[t];
  if (sum != 6)
    abort ();

  sum = 0;
  GOMP_parallel (body_sumprod, &dsp, 0, 0);
  sum = 0;
  prod = 1;
  for (t = 0; t < dsp.nt; t++)
    {
      sum += dsp.priv_s[t];
      prod *= dsp.priv_p[t];
    }
  if (sum != 6 || prod != 8)
    abort ();

  sum = 0;
  prod = 1;
  GOMP_parallel (body_sumprod, &dsp, 0, 0);
  sum = 0;
  prod = 1;
  for (t = 0; t < dsp.nt; t++)
    {
      sum += dsp.priv_s[t];
      prod *= dsp.priv_p[t];
    }
  if (sum != 6 || prod != 8)
    abort ();
  return 0;
}
