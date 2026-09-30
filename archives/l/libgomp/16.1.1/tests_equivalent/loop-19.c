/* Equiv-rewrite of upstream loop-19.c (same lowering as loop-18.c). */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

int x, i, j;
volatile int a, b, c, d, e, f, g, h;
int k[16][67];

int niters;
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

static void iter1 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = ii * 2 + 1; jj < 4 * ii + 3; jj++)
    { if (ii < 0 || ii >= 16 || jj < 2 * ii + 1 || jj >= 3 + ii * 4 || k[ii][jj] != c->expected) abort ();
      k[ii][jj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter2 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = ii * 2 + 1; jj < 2 * ii + 7; jj++)
    { if (ii < 0 || ii >= 16 || jj < 2 * ii + 1 || jj >= 7 + ii * 2 || k[ii][jj] != c->expected) abort ();
      k[ii][jj]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (i = 0; i < 16; i++)
    for (j = i * 2 + 1; j < 4 * i + 3; j++)
      k[i][j] = 1;
  a = 0; b = 16; c = 1; d = 2; e = 1; f = 4; g = 3; h = 1;

  niters = 0; x = -100;
  run_block (iter1, &c1, 0, 16, 1);
  for (i = 0; i < 16; i++) for (j = i * 2 + 1; j < 4 * i + 3; j++) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 63 || x != 15422 || niters != 272) abort ();
  niters = 0; x = -100;
  run_block (iter1, &c2, 0, 16, 1);
  for (i = 0; i < 16; i++) for (j = i * 2 + 1; j < 4 * i + 3; j++) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 63 || x != 15422 || niters != 272) abort ();
  for (i = 0; i < 16; i++)
    for (j = i * 2 + 1; j < 4 * i + 3; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 16; i++)
    for (j = i * 2 + 1; j < 2 * i + 7; j++)
      k[i][j] = 1;
  a = 0; b = 16; c = 1; d = 2; e = 1; f = 2; g = 7; h = 1;

  niters = 0; x = -100;
  run_block (iter2, &c1, 0, 16, 1);
  for (i = 0; i < 16; i++) for (j = i * 2 + 1; j < 2 * i + 7; j++) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 37 || x != 15396 || niters != 96) abort ();
  niters = 0; x = -100;
  run_block (iter2, &c2, 0, 16, 1);
  for (i = 0; i < 16; i++) for (j = i * 2 + 1; j < 2 * i + 7; j++) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 37 || x != 15396 || niters != 96) abort ();
  for (i = 0; i < 16; i++)
    for (j = i * 2 + 1; j < 2 * i + 7; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();

  free (niters_priv);
  return 0;
}
