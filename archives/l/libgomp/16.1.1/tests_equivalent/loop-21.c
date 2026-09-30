/* Equiv-rewrite of upstream loop-21.c (same lowering as loop-18.c, but with
 * descending outer loops and several negative-stride inner loops).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

int x, i, j;
volatile int a, b, c, d, e, f, g, h;
int k[13][27];

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
  for (jj = 3 * ii; jj > 2 * ii; jj--)
    { if (ii < -4 || ii >= 8 || jj > 3 * ii || jj <= ii * 2 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter2 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = -2 * ii + 3; jj > -3; jj -= 2)
    { if (ii < -2 || ii >= 4 || jj <= -3 || jj > -2 * ii + 3 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter3 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = -2 * ii + 7; jj > 2 * ii + 1; jj--)
    { if (ii <= -3 || ii > 3 || jj <= 2 * ii + 1 || jj > -2 * ii + 7 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter4 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 2 * ii + 7; jj > -2 * ii + 1; jj--)
    { if (ii <= -3 || ii > 3 || jj <= -2 * ii + 1 || jj > 2 * ii + 7 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter5 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 2 * ii + 7; jj <= -2 * ii + 1; jj++)
    { if (ii <= -6 || ii > 6 || jj < 2 * ii + 7 || jj >= -2 * ii + 2 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter6 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = -2 * ii + 7; jj <= 2 * ii + 1; jj++)
    { if (ii <= -6 || ii > 6 || jj < -2 * ii + 7 || jj >= 2 * ii + 2 || k[ii + 5][jj + 5] != c->expected) abort ();
      k[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };
  int li, lj;

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (i = -4; i < 8; i++)
    for (j = 3 * i; j > 2 * i; j--)
      k[i + 5][j + 5] = 1;
  a = -4; b = 8; c = 1; d = 3; e = 0; f = 2; g = 0; h = -1;

  niters = 0; x = -100;
  run_block (iter1, &c1, -4, 8, 1);
  for (i = -4; i < 8; i++) for (j = 3 * i; j > 2 * i; j--) x = i * 1024 + (j & 1023);
  if (i != 8 || j != 14 || x != 7183 || niters != 28) abort ();
  niters = 0; x = -100;
  run_block (iter1, &c2, -4, 8, 1);
  for (i = -4; i < 8; i++) for (j = 3 * i; j > 2 * i; j--) x = i * 1024 + (j & 1023);
  if (i != 8 || j != 14 || x != 7183 || niters != 28) abort ();
  for (li = -4; li < 8; li++)
    for (lj = 3 * li; lj > 2 * li; lj--)
      if (k[li + 5][lj + 5] == 3) k[li + 5][lj + 5] = 0; else abort ();

  for (i = -2; i < 4; i++)
    for (j = -2 * i + 3; j > -3; j -= 2)
      k[i + 5][j + 5] = 1;
  a = -2; b = 4; c = 1; d = -2; e = 3; f = 0; g = -3; h = -2;

  niters = 0; x = -100;
  run_block (iter2, &c1, -2, 4, 1);
  for (i = -2; i < 4; i++) for (j = -2 * i + 3; j > -3; j -= 2) x = i * 1024 + (j & 1023);
  if (x != 3071 || niters != 15) abort ();
  niters = 0; x = -100;
  run_block (iter2, &c2, -2, 4, 1);
  for (i = -2; i < 4; i++) for (j = -2 * i + 3; j > -3; j -= 2) x = i * 1024 + (j & 1023);
  if (x != 3071 || niters != 15) abort ();
  for (i = -2; i < 4; i++)
    for (j = -2 * i + 3; j > -3; j -= 2)
      if (k[i + 5][j + 5] == 3) k[i + 5][j + 5] = 0; else abort ();

  for (i = 3; i > -3; i--)
    for (j = -2 * i + 7; j > 2 * i + 1; j--)
      k[i + 5][j + 5] = 1;
  a = 3; b = -3; c = -1; d = -2; e = 7; f = 2; g = 1; h = -1;

  niters = 0; x = -100;
  run_block (iter3, &c1, 3, -3, -1);
  for (i = 3; i > -3; i--) for (j = -2 * i + 7; j > 2 * i + 1; j--) x = i * 1024 + (j & 1023);
  if (i != -3 || j != -3 || x != -1026 || niters != 32) abort ();
  niters = 0; x = -100;
  run_block (iter3, &c2, 3, -3, -1);
  for (i = 3; i > -3; i--) for (j = -2 * i + 7; j > 2 * i + 1; j--) x = i * 1024 + (j & 1023);
  if (i != -3 || j != -3 || x != -1026 || niters != 32) abort ();
  for (i = 3; i > -3; i--)
    for (j = -2 * i + 7; j > 2 * i + 1; j--)
      if (k[i + 5][j + 5] == 3) k[i + 5][j + 5] = 0; else abort ();

  for (i = 3; i > -3; i--)
    for (j = 2 * i + 7; j > -2 * i + 1; j--)
      k[i + 5][j + 5] = 1;
  a = 3; b = -3; c = -1; d = 2; e = 7; f = -2; g = 1; h = -1;

  niters = 0; x = -100;
  run_block (iter4, &c1, 3, -3, -1);
  for (i = 3; i > -3; i--) for (j = 2 * i + 7; j > -2 * i + 1; j--) x = i * 1024 + (j & 1023);
  if (x != -1020 || niters != 50) abort ();
  niters = 0; x = -100;
  run_block (iter4, &c2, 3, -3, -1);
  for (i = 3; i > -3; i--) for (j = 2 * i + 7; j > -2 * i + 1; j--) x = i * 1024 + (j & 1023);
  if (x != -1020 || niters != 50) abort ();
  for (i = 3; i > -3; i--)
    for (j = 2 * i + 7; j > -2 * i + 1; j--)
      if (k[i + 5][j + 5] == 3) k[i + 5][j + 5] = 0; else abort ();

  for (i = 6; i > -6; i--)
    for (j = 2 * i + 7; j <= -2 * i + 1; j++)
      k[i + 5][j + 5] = 1;
  a = 6; b = -6; c = -1; d = 2; e = 7; f = -2; g = 2; h = 1;

  niters = 0; x = -100;
  run_block (iter5, &c1, 6, -6, -1);
  for (i = 6; i > -6; i--) for (j = 2 * i + 7; j <= -2 * i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != -6 || j != 12 || x != -5109 || niters != 36) abort ();
  niters = 0; x = -100;
  run_block (iter5, &c2, 6, -6, -1);
  for (i = 6; i > -6; i--) for (j = 2 * i + 7; j <= -2 * i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != -6 || j != 12 || x != -5109 || niters != 36) abort ();
  for (i = 6; i > -6; i--)
    for (j = 2 * i + 7; j <= -2 * i + 1; j++)
      if (k[i + 5][j + 5] == 3) k[i + 5][j + 5] = 0; else abort ();

  for (i = 6; i > -6; i -= 2)
    for (j = -2 * i + 7; j <= 2 * i + 1; j++)
      k[i + 5][j + 5] = 1;
  a = 6; b = -6; c = -2; d = -2; e = 7; f = 2; g = 2; h = 1;

  niters = 0; x = -100;
  run_block (iter6, &c1, 6, -6, -2);
  for (i = 6; i > -6; i -= 2) for (j = -2 * i + 7; j <= 2 * i + 1; j++) x = i * 1024 + (j & 1023);
  if (x != 2053 || niters != 33) abort ();
  niters = 0; x = -100;
  run_block (iter6, &c2, 6, -6, -2);
  for (i = 6; i > -6; i -= 2) for (j = -2 * i + 7; j <= 2 * i + 1; j++) x = i * 1024 + (j & 1023);
  if (x != 2053 || niters != 33) abort ();
  for (i = 6; i > -6; i -= 2)
    for (j = -2 * i + 7; j <= 2 * i + 1; j++)
      if (k[i + 5][j + 5] == 3) k[i + 5][j + 5] = 0; else abort ();

  free (niters_priv);
  return 0;
}
