/* Equiv-rewrite of upstream loop-18.c.
 * Each `parallel for collapse(2) lastprivate(i,j,x) reduction(+:niters)` is
 * lowered by distributing the OUTER loop across threads (GOMP_loop_static),
 * running the inner loop to completion, reducing niters per-thread, and then
 * reproducing lastprivate(i,j,x) with a serial dry-run of the same loop (the
 * sequential exit values).  The body never touches the shared x (lastprivate).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

int x, i, j;
volatile int a, b, c, d, e, f, g, h;
int k[11][101];

int niters;
int *niters_priv;
int nt;

static void
combine (void)
{
  int t;
  for (t = 0; t < nt; t++)
    {
      niters += niters_priv[t];
      niters_priv[t] = 0;
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

static void iter1 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 1; jj <= 10 * ii; jj++)
    { if (ii < 1 || ii > 10 || jj < 1 || jj > 10 * ii || k[ii][jj] != c->expected) abort ();
      k[ii][jj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter2 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 0; jj < 10 * ii; jj++)
    { if (ii < 0 || ii >= 10 || jj < 0 || jj >= 10 * ii || k[ii][jj] != c->expected) abort ();
      k[ii][jj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter3 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = -9 + 2 * ii; jj < ii; jj++)
    { if (ii < 4 || ii >= 10 || jj < -9 + 2 * ii || jj >= ii || k[ii][jj + 1] != c->expected) abort ();
      k[ii][jj + 1]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter4 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 1; jj < ii + 1; jj++)
    { if (ii < 1 || ii >= 10 || jj < 1 || jj >= ii + 1 || k[ii][jj] != c->expected) abort ();
      k[ii][jj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter5 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = -8 * ii - 9; jj < ii * -3 + 6; jj += 15)
    { if (ii != 4 || jj < -41 || jj > -11 || k[0][-jj] != c->expected) abort ();
      k[0][-jj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter6 (void *ctx, long ii) { struct c1 *c = ctx; int jj;
  for (jj = 3 * ii + 5; jj < -6; jj++)
    { if (ii != -13 || jj < -34 || jj > -7 || k[0][-jj] != c->expected) abort ();
      k[0][-jj]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };
  int t;

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (i = 1; i <= 10; i++)
    for (j = 1; j <= 10 * i; j++)
      k[i][j] = 1;
  a = 1; b = 11; c = 1; d = 0; e = 1; f = 10; g = 1; h = 1;

  /* pair 1 */
  niters = 0; x = -100;
  run_block (iter1, &c1, 1, 11, 1);
  for (i = 1; i <= 10; i++) for (j = 1; j <= 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 101 || x != 10340 || niters != 550) abort ();
  niters = 0; x = -100;
  run_block (iter1, &c2, 1, 11, 1);
  for (i = 1; i <= 10; i++) for (j = 1; j <= 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 101 || x != 10340 || niters != 550) abort ();
  for (i = 1; i <= 10; i++)
    for (j = 1; j <= 10 * i; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 0; i < 10; i++)
    for (j = 0; j < 10 * i; j++)
      k[i][j] = 1;
  a = 0; b = 10; c = 1; d = 0; e = 0; f = 10; g = 0; h = 1;

  /* pair 2 */
  niters = 0; x = -100;
  run_block (iter2, &c1, 0, 10, 1);
  for (i = 0; i < 10; i++) for (j = 0; j < 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 10 || j != 90 || x != 9305 || niters != 450) abort ();
  niters = 0; x = -100;
  run_block (iter2, &c2, 0, 10, 1);
  for (i = 0; i < 10; i++) for (j = 0; j < 10 * i; j++) x = i * 1024 + (j & 1023);
  if (i != 10 || j != 90 || x != 9305 || niters != 450) abort ();
  for (i = 0; i < 10; i++)
    for (j = 0; j < 10 * i; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 4; i < 10; i++)
    for (j = -9 + 2 * i; j < i; j++)
      k[i][j + 1] = 1;
  a = 4; b = 10; c = 1; d = 2; e = -9; f = 1; g = 0; h = 1;

  /* pair 3 */
  niters = 0; x = -100;
  run_block (iter3, &c1, 4, 10, 1);
  for (i = 4; i < 10; i++) for (j = -9 + 2 * i; j < i; j++) x = i * 1024 + (j & 1023);
  if (x != 8199 || niters != 15) abort ();
  niters = 0; x = -100;
  run_block (iter3, &c2, 4, 10, 1);
  for (i = 4; i < 10; i++) for (j = -9 + 2 * i; j < i; j++) x = i * 1024 + (j & 1023);
  if (x != 8199 || niters != 15) abort ();
  for (i = 4; i < 10; i++)
    for (j = -9 + 2 * i; j < i; j++)
      if (k[i][j + 1] == 3) k[i][j + 1] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (i = 1; i < 10; i += 2)
    for (j = 1; j < i + 1; j++)
      k[i][j] = 1;
  a = 1; b = 10; c = 2; d = 0; e = 1; f = 1; g = 1; h = 1;

  /* pair 4 */
  niters = 0; x = -100;
  run_block (iter4, &c1, 1, 10, 2);
  for (i = 1; i < 10; i += 2) for (j = 1; j < i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 10 || x != 9225 || niters != 25) abort ();
  niters = 0; x = -100;
  run_block (iter4, &c2, 1, 10, 2);
  for (i = 1; i < 10; i += 2) for (j = 1; j < i + 1; j++) x = i * 1024 + (j & 1023);
  if (i != 11 || j != 10 || x != 9225 || niters != 25) abort ();
  for (i = 1; i < 10; i += 2)
    for (j = 1; j < i + 1; j++)
      if (k[i][j] == 3) k[i][j] = 0; else abort ();
  for (i = 0; i < 11; i++)
    for (j = 0; j < 101; j++)
      if (k[i][j] != 0) abort ();

  for (j = -11; j >= -41; j -= 15)
    k[0][-j] = 1;
  a = 4; b = 8; c = 12; d = -8; e = -9; f = -3; g = 6; h = 15;

  /* pair 5 */
  niters = 0; x = -100;
  run_block (iter5, &c1, 4, 8, 12);
  for (i = 4; i < 8; i += 12) for (j = -8 * i - 9; j < i * -3 + 6; j += 15) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 4 || x != 5109 || niters != 3) abort ();
  niters = 0; x = -100;
  run_block (iter5, &c2, 4, 8, 12);
  for (i = 4; i < 8; i += 12) for (j = -8 * i - 9; j < i * -3 + 6; j += 15) x = i * 1024 + (j & 1023);
  if (i != 16 || j != 4 || x != 5109 || niters != 3) abort ();
  for (j = -11; j >= -41; j -= 15)
    if (k[0][-j] == 3) k[0][-j] = 0; else abort ();
  for (j = -11; j >= -41; j--)
    if (k[0][-j] != 0) abort ();

  for (j = -34; j <= -7; j++)
    k[0][-j] = 1;
  a = -13; b = 7; c = 12; d = 3; e = 5; f = 0; g = -6; h = 1;

  /* pair 6 */
  niters = 0; x = -100;
  run_block (iter6, &c1, -13, 7, 12);
  for (i = -13; i < 7; i += 12) for (j = 3 * i + 5; j < -6; j++) x = i * 1024 + (j & 1023);
  if (x != -12295 || niters != 28) abort ();
  niters = 0; x = -100;
  run_block (iter6, &c2, -13, 7, 12);
  for (i = -13; i < 7; i += 12) for (j = 3 * i + 5; j < -6; j++) x = i * 1024 + (j & 1023);
  if (x != -12295 || niters != 28) abort ();
  for (j = -34; j <= -7; j++)
    if (k[0][-j] == 3) k[0][-j] = 0; else abort ();

  free (niters_priv);
  return 0;
}
