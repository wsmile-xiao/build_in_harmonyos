/* Equiv-rewrite of upstream loop-20.c (unsigned long long loop variables;
 * the outer loop is distributed and the huge inner loop runs serially per
 * outer iteration, so no unsigned worksharing is needed for the inner loop).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

unsigned long long int x, i, j;
volatile unsigned long long int a, b, c, d, e, f, g, h;
int k[4][206];

long long int niters;
int *niters_priv;
int nt;

static void
combine (void)
{
  int t;
  for (t = 0; t < nt; t++)
    { niters += niters_priv[t]; niters_priv[t] = 0; }
}

static void
run_block (void (*iter) (void *, long), void *ctx, long s, long e, long inc)
{
  struct b2g2_ws ws = { ctx, iter, 0, s, e, inc, 0 };
  b2g2_parallel_for (&ws, 0);
  combine ();
}

struct c1 { int expected; };

static void iter1 (void *ctx, long ii) { struct c1 *c = ctx; unsigned long long jj;
  unsigned long long u = (unsigned long long) ii;
  for (jj = ~0ULL / 2 - 32; jj < u * ((~0ULL / 2) + 6); jj++)
    { if (u != 1 || jj < ~0ULL / 2 - 32 || jj >= ((~0ULL / 2) + 6) || k[0][jj - ~0ULL / 2 + 64] != c->expected) abort ();
      k[0][jj - ~0ULL / 2 + 64]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter2 (void *ctx, long ii) { struct c1 *c = ctx; unsigned long long jj;
  unsigned long long u = (unsigned long long) ii;
  for (jj = 64ULL * u; jj < u * 32ULL + 110; jj++)
    { if (u < 1 || u >= 4 || jj < 64ULL * u || jj >= u * 32ULL + 110 || k[u][jj] != c->expected) abort ();
      k[u][jj]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (j = ~0ULL / 2 - 32; j < ((~0ULL / 2) + 6); j++)
    k[0][j - ~0ULL / 2 + 64] = 1;
  a = 1; b = 2; c = 1; d = 0; e = ~0ULL / 2 - 32; f = ((~0ULL / 2) + 6); g = 0; h = 1;

  niters = 0; x = (unsigned long long) -100;
  run_block (iter1, &c1, 1, 2, 1);
  for (i = 1; i < 2; i++) for (j = ~0ULL / 2 - 32; j < i * ((~0ULL / 2) + 6); j++) x = i * 1024 + (j & 1023);
  if (i != 2 || j != ((~0ULL / 2) + 6) || x != 1028 || niters != 38) abort ();
  niters = 0; x = (unsigned long long) -100;
  run_block (iter1, &c2, 1, 2, 1);
  for (i = 1; i < 2; i++) for (j = ~0ULL / 2 - 32; j < i * ((~0ULL / 2) + 6); j++) x = i * 1024 + (j & 1023);
  if (i != 2 || j != ((~0ULL / 2) + 6) || x != 1028 || niters != 38) abort ();
  for (j = ~0ULL / 2 - 32; j < ((~0ULL / 2) + 6); j++)
    if (k[0][j - ~0ULL / 2 + 64] == 3) k[0][j - ~0ULL / 2 + 64] = 0; else abort ();

  for (i = 1; i < 4; i++)
    for (j = 64ULL * i; j < i * 32ULL + 110; j++)
      k[i][j] = 1;
  a = 1; b = 4; c = 1; d = 64ULL; e = 0; f = 32ULL; g = 110ULL; h = 1;

  niters = 0; x = (unsigned long long) -100;
  run_block (iter2, &c1, 1, 4, 1);
  for (i = 1; i < 4; i++) for (j = 64ULL * i; j < i * 32ULL + 110; j++) x = i * 1024 + (j & 1023);
  if (i != 4 || j != 206 || x != 3277 || niters != 138) abort ();
  niters = 0; x = (unsigned long long) -100;
  run_block (iter2, &c2, 1, 4, 1);
  for (i = 1; i < 4; i++) for (j = 64ULL * i; j < i * 32ULL + 110; j++) x = i * 1024 + (j & 1023);
  if (i != 4 || j != 206 || x != 3277 || niters != 138) abort ();
  for (i = 1; i < 4; i++)
    for (j = 64ULL * i; j < i * 32ULL + 110; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();

  free (niters_priv);
  return 0;
}
