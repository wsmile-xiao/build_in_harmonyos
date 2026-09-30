/* Equiv-rewrite of upstream loop-25.c.
 * `parallel for simd collapse(2) lastprivate(i,j,x) reduction(+:niters)
 *  reduction(|:err)`.  simd is a vectorization hint, so this is a parallel for.
 *  Same lowering as loop-18.c, plus a per-thread OR reduction for err.
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

int x, i, j;
volatile int a, b, c, d, e, f, g, h;
int k[11][101];

int niters;
int err;
int *niters_priv;
int *err_priv;
int nt;

static void
combine (void)
{
  int t;
  for (t = 0; t < nt; t++)
    {
      niters += niters_priv[t];
      niters_priv[t] = 0;
      err |= err_priv[t];
      err_priv[t] = 0;
    }
}

static void
run_block (void (*iter) (void *, long), void *ctx, long s, long e, long inc)
{
  struct b2g2_ws ws = { ctx, iter, 0, s, e, inc, 0 };
  b2g2_parallel_for (&ws, 0);
  combine ();
}

struct c1 { int expected; };

static void iter1 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = 1; jj <= 10 * ii; jj++)
    { err_priv[t] |= (ii < 1); err_priv[t] |= (ii > 10); err_priv[t] |= (jj < 1); err_priv[t] |= (jj > 10 * ii); err_priv[t] |= (k[ii][jj] != c->expected);
      k[ii][jj]++; niters_priv[t]++; } }

static void iter2 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = 0; jj < 10 * ii; jj++)
    { err_priv[t] |= (ii < 0); err_priv[t] |= (ii >= 10); err_priv[t] |= (jj < 0); err_priv[t] |= (jj >= 10 * ii); err_priv[t] |= (k[ii][jj] != c->expected);
      k[ii][jj]++; niters_priv[t]++; } }

static void iter3 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = -9 + 2 * ii; jj < ii; jj++)
    { err_priv[t] |= (ii < 4); err_priv[t] |= (ii >= 10); err_priv[t] |= (jj < -9 + 2 * ii); err_priv[t] |= (jj >= ii); err_priv[t] |= (k[ii][jj + 1] != c->expected);
      k[ii][jj + 1]++; niters_priv[t]++; } }

static void iter4 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = 1; jj < ii + 1; jj++)
    { err_priv[t] |= (ii < 1); err_priv[t] |= (ii >= 10); err_priv[t] |= (jj < 1); err_priv[t] |= (jj >= ii + 1); err_priv[t] |= (k[ii][jj] != c->expected);
      k[ii][jj]++; niters_priv[t]++; } }

static void iter5 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = -8 * ii - 9; jj < ii * -3 + 6; jj += 15)
    { err_priv[t] |= (ii != 4); err_priv[t] |= (jj < -41); err_priv[t] |= (jj > -11); err_priv[t] |= (k[0][-jj] != c->expected);
      k[0][-jj]++; niters_priv[t]++; } }

static void iter6 (void *ctx, long ii) { struct c1 *c = ctx; int jj, t = omp_get_thread_num ();
  for (jj = 3 * ii + 5; jj < -6; jj++)
    { err_priv[t] |= (ii != -13); err_priv[t] |= (jj < -34); err_priv[t] |= (jj > -7); err_priv[t] |= (k[0][-jj] != c->expected);
      k[0][-jj]++; niters_priv[t]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));
  err_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (i = 1; i <= 10; i++)
    for (j = 1; j <= 10 * i; j++)
      { k[i][j] = 1; asm volatile ("" : : : "memory"); }
  a = 1; b = 11; c = 1; d = 0; e = 1; f = 10; g = 1; h = 1;

  niters = 0; err = 0; x = -100;
  run_block (iter1, &c1, 1, 11, 1);
  for (i = 1; i <= 10; i++) for (j = 1; j <= 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 101 || x != 10340 || niters != 550 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter1, &c2, 1, 11, 1);
  for (i = 1; i <= 10; i++) for (j = 1; j <= 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 101 || x != 10340 || niters != 550 || err) abort ();
  for (i = 1; i <= 10; i++)
    for (j = 1; j <= 10 * i; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 0; i < 10; i++)
    for (j = 0; j < 10 * i; j++)
      { k[i][j] = 1; asm volatile ("" : : : "memory"); }
  a = 0; b = 10; c = 1; d = 0; e = 0; f = 10; g = 0; h = 1;

  niters = 0; err = 0; x = -100;
  run_block (iter2, &c1, 0, 10, 1);
  for (i = 0; i < 10; i++) for (j = 0; j < 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 10 || j != 90 || x != 9305 || niters != 450 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter2, &c2, 0, 10, 1);
  for (i = 0; i < 10; i++) for (j = 0; j < 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 10 || j != 90 || x != 9305 || niters != 450 || err) abort ();
  for (i = 0; i < 10; i++)
    for (j = 0; j < 10 * i; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 4; i < 10; i++)
    for (j = -9 + 2 * i; j < i; j++)
      { k[i][j + 1] = 1; asm volatile ("" : : : "memory"); }
  a = 4; b = 10; c = 1; d = 2; e = -9; f = 1; g = 0; h = 1;

  niters = 0; err = 0; x = -100;
  run_block (iter3, &c1, 4, 10, 1);
  for (i = 4; i < 10; i++) for (j = -9 + 2 * i; j < i; j++) x = i * 1024 + (j & 1023);
  if (x != 8199 || niters != 15 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter3, &c2, 4, 10, 1);
  for (i = 4; i < 10; i++) for (j = -9 + 2 * i; j < i; j++) x = i * 1024 + (j & 1023);
  if (x != 8199 || niters != 15 || err) abort ();
  for (i = 4; i < 10; i++)
    for (j = -9 + 2 * i; j < i; j++)
      if (k[i][j + 1] == 3) k[i][j + 1] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 1; i < 10; i += 2)
    for (j = 1; j < i + 1; j++)
      { k[i][j] = 1; asm volatile ("" : : : "memory"); }
  a = 1; b = 10; c = 2; d = 0; e = 1; f = 1; g = 1; h = 1;

  niters = 0; err = 0; x = -100;
  run_block (iter4, &c1, 1, 10, 2);
  for (i = 1; i < 10; i += 2) for (j = 1; j < i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 10 || x != 9225 || niters != 25 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter4, &c2, 1, 10, 2);
  for (i = 1; i < 10; i += 2) for (j = 1; j < i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 10 || x != 9225 || niters != 25 || err) abort ();
  for (i = 1; i < 10; i += 2)
    for (j = 1; j < i + 1; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (j = -11; j >= -41; j -= 15)
    { k[0][-j] = 1; asm volatile ("" : : : "memory"); }
  a = 4; b = 8; c = 12; d = -8; e = -9; f = -3; g = 6; h = 15;

  niters = 0; err = 0; x = -100;
  run_block (iter5, &c1, 4, 8, 12);
  for (i = 4; i < 8; i += 12) for (j = -8 * i - 9; j < i * -3 + 6; j += 15) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 4 || x != 5109 || niters != 3 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter5, &c2, 4, 8, 12);
  for (i = 4; i < 8; i += 12) for (j = -8 * i - 9; j < i * -3 + 6; j += 15) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 4 || x != 5109 || niters != 3 || err) abort ();
  for (j = -11; j >= -41; j -= 15)
    if (k[0][-j] == 3) k[0][-j] = 0; else abort ();
  for (j = -11; j >= -41; j--)
    if (k[0][-j] != 0) abort ();

  for (j = -34; j <= -7; j++)
    { k[0][-j] = 1; asm volatile ("" : : : "memory"); }
  a = -13; b = 7; c = 12; d = 3; e = 5; f = 0; g = -6; h = 1;

  niters = 0; err = 0; x = -100;
  run_block (iter6, &c1, -13, 7, 12);
  for (i = -13; i < 7; i += 12) for (j = 3 * i + 5; j < -6; j++) x = i * 1024 + (j & 1023);
  if (x != -12295 || niters != 28 || err) abort ();
  niters = 0; err = 0; x = -100;
  run_block (iter6, &c2, -13, 7, 12);
  for (i = -13; i < 7; i += 12) for (j = 3 * i + 5; j < -6; j++) x = i * 1024 + (j & 1023);
  if (x != -12295 || niters != 28 || err) abort ();
  for (j = -34; j <= -7; j++)
    if (k[0][-j] == 3) k[0][-j] = 0; else abort ();

  free (niters_priv);
  free (err_priv);
  return 0;
}
