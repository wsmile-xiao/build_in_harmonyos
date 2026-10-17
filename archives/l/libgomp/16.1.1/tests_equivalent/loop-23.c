/* Equiv-rewrite of upstream loop-23.c.
 * `teams reduction` is a no-op for a single host team; the inner
 * `distribute parallel for` is a real parallel for, lowered by distributing
 * the outer loop (GOMP_loop_static) and reducing niters per-thread.
 * Part 1 = collapse(7/5/3) counter; Part 2 = collapse(2) lastprivate (same as
 * loop-21) with a serial dry-run for lastprivate(i,j,x).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

signed char v[5][7][9][21][4][42][3];
volatile int zero = 0, one = 1, two = 2, three = 3;
volatile int five = 5, seven = 7, nine = 9, eleven = 11;

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

struct c { int expected; };

static void iter7 (void *ctx, long i_) { struct c *c = ctx; int j, k, l, m, n, o, t = omp_get_thread_num ();
  for (j = 0; j < 7; j++)
    for (k = 0; k < 9; k++)
      for (l = 2 * j; l < 3 * j; l++)
	for (m = 7; m < 11; m++)
	  for (n = l; n < 2 * l; n++)
	    for (o = 0; o < 3; o++)
	      {
		niters_priv[t]++;
		if (i_ < 0 || i_ >= 5 || j < 0 || j >= 7 || k < 0 || k >= 9
		    || l < 2 * j || l >= 3 * j || m < 7 || m >= 11
		    || n < l || n >= 2 * l || o < 0 || o >= 3)
		  abort ();
		if (v[i_][j][k][l][m - 7][n][o] != c->expected)
		  abort ();
		v[i_][j][k][l][m - 7][n][o]++;
	      } }

static void iter5 (void *ctx, long i_) { struct c *c = ctx; int j, l, n, o, t = omp_get_thread_num ();
  for (j = 6; j >= 0; --j)
    for (l = 3 * j - 1; l >= 2 * j; l--)
      for (n = 2 * l + -1; n > l - 1; --n)
	for (o = 2; o >= 0; o--)
	  {
	    niters_priv[t]++;
	    if (i_ < 0 || i_ >= 5 || j < 0 || j >= 7 || l < 2 * j || l >= 3 * j
		|| n < l || n >= 2 * l || o < 0 || o >= 3)
	      abort ();
	    if (v[i_][j][0][l][0][n][o] != c->expected)
	      abort ();
	    v[i_][j][0][l][0][n][o]++;
	  } }

static void iter3 (void *ctx, long j_) { struct c *c = ctx; int l, n, t = omp_get_thread_num ();
  for (l = 2 * j_; l <= 3 * j_ - 1; l++)
    for (n = 2 * l + -1; n > l - 1; --n)
      {
	niters_priv[t]++;
	if (j_ < 0 || j_ >= 7 || l < 2 * j_ || l >= 3 * j_ || n < l || n >= 2 * l)
	  abort ();
	if (v[0][j_][0][l][0][n][0] != c->expected)
	  abort ();
	v[0][j_][0][l][0][n][0]++;
      } }

/* ---- Part 2 (collapse(2) lastprivate over static w[13][27]) ---- */

static int wi, wj, wx;
static volatile int wa, wb, wc, wd, we, wf, wg, wh;
static int w[13][27];

static void witer1 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = 3 * ii; jj > 2 * ii; jj--)
    { if (ii < -4 || ii >= 8 || jj > 3 * ii || jj <= ii * 2 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void witer2 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = -2 * ii + 3; jj > -3; jj -= 2)
    { if (ii < -2 || ii >= 4 || jj <= -3 || jj > -2 * ii + 3 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void witer3 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = -2 * ii + 7; jj > 2 * ii + 1; jj--)
    { if (ii <= -3 || ii > 3 || jj <= 2 * ii + 1 || jj > -2 * ii + 7 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void witer4 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = 2 * ii + 7; jj > -2 * ii + 1; jj--)
    { if (ii <= -3 || ii > 3 || jj <= -2 * ii + 1 || jj > 2 * ii + 7 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void witer5 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = 2 * ii + 7; jj <= -2 * ii + 1; jj++)
    { if (ii <= -6 || ii > 6 || jj < 2 * ii + 7 || jj >= -2 * ii + 2 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

static void witer6 (void *ctx, long ii) { struct c *c = ctx; int jj;
  for (jj = -2 * ii + 7; jj <= 2 * ii + 1; jj++)
    { if (ii <= -6 || ii > 6 || jj < -2 * ii + 7 || jj >= 2 * ii + 2 || w[ii + 5][jj + 5] != c->expected) abort ();
      w[ii + 5][jj + 5]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c c1 = { 1 }, c2 = { 2 }, c3 = { 3 }, c4 = { 4 }, c5 = { 5 }, c6 = { 6 };
  int i, j, k, l, m, n, o, li, lj;

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (k = 0; k < 9; k++)
	for (l = 2 * j; l < 3 * j; l++)
	  for (m = 7; m < 11; m++)
	    for (n = l; n < 2 * l; n++)
	      for (o = 0; o < 3; o++)
		v[i][j][k][l][m - 7][n][o] = 1;

  niters = 0; run_block (iter7, &c1, 0, 5, 1);
  if (niters != 117180) abort ();
  niters = 0; run_block (iter7, &c2, 0, 5, 1);
  if (niters != 117180) abort ();
  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (k = 0; k < 9; k++)
	for (l = 2 * j; l < 3 * j; l++)
	  for (m = 7; m < 11; m++)
	    for (n = l; n < 2 * l; n++)
	      for (o = 0; o < 3; o++)
		if (v[i][j][k][l][m - 7][n][o] != 3) abort ();

  niters = 0; run_block (iter5, &c3, 0, 5, 1);
  if (niters != 3255) abort ();
  niters = 0; run_block (iter5, &c4, 0, 5, 1);
  if (niters != 3255) abort ();
  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (l = 2 * j; l < 3 * j; l++)
	for (n = l; n < 2 * l; n++)
	  for (o = 0; o < 3; o++)
	    if (v[i][j][0][l][0][n][o] != 5) abort ();

  niters = 0; run_block (iter3, &c5, 0, 7, 1);
  if (niters != 217) abort ();
  niters = 0; run_block (iter3, &c6, 0, 7, 1);
  if (niters != 217) abort ();
  for (j = 0; j < 7; j++)
    for (l = 2 * j; l < 3 * j; l++)
      for (n = l; n < 2 * l; n++)
	if (v[0][j][0][l][0][n][0] != 7) abort ();

  /* Part 2 */
  for (wi = -4; wi < 8; wi++)
    for (wj = 3 * wi; wj > 2 * wi; wj--)
      w[wi + 5][wj + 5] = 1;
  wa = -4; wb = 8; wc = 1; wd = 3; we = 0; wf = 2; wg = 0; wh = -1;

  niters = 0; wx = -100;
  run_block (witer1, &c1, -4, 8, 1);
  for (wi = -4; wi < 8; wi++) for (wj = 3 * wi; wj > 2 * wi; wj--) wx = wi * 1024 + (wj & 1023);
  if (wi != 8 || wj != 14 || wx != 7183 || niters != 28) abort ();
  niters = 0; wx = -100;
  run_block (witer1, &c2, -4, 8, 1);
  for (wi = -4; wi < 8; wi++) for (wj = 3 * wi; wj > 2 * wi; wj--) wx = wi * 1024 + (wj & 1023);
  if (wi != 8 || wj != 14 || wx != 7183 || niters != 28) abort ();
  for (li = -4; li < 8; li++)
    for (lj = 3 * li; lj > 2 * li; lj--)
      if (w[li + 5][lj + 5] == 3) w[li + 5][lj + 5] = 0; else abort ();

  for (wi = -2; wi < 4; wi++)
    for (wj = -2 * wi + 3; wj > -3; wj -= 2)
      w[wi + 5][wj + 5] = 1;
  wa = -2; wb = 4; wc = 1; wd = -2; we = 3; wf = 0; wg = -3; wh = -2;

  niters = 0; wx = -100;
  run_block (witer2, &c1, -2, 4, 1);
  for (wi = -2; wi < 4; wi++) for (wj = -2 * wi + 3; wj > -3; wj -= 2) wx = wi * 1024 + (wj & 1023);
  if (wx != 3071 || niters != 15) abort ();
  niters = 0; wx = -100;
  run_block (witer2, &c2, -2, 4, 1);
  for (wi = -2; wi < 4; wi++) for (wj = -2 * wi + 3; wj > -3; wj -= 2) wx = wi * 1024 + (wj & 1023);
  if (wx != 3071 || niters != 15) abort ();
  for (wi = -2; wi < 4; wi++)
    for (wj = -2 * wi + 3; wj > -3; wj -= 2)
      if (w[wi + 5][wj + 5] == 3) w[wi + 5][wj + 5] = 0; else abort ();

  for (wi = 3; wi > -3; wi--)
    for (wj = -2 * wi + 7; wj > 2 * wi + 1; wj--)
      w[wi + 5][wj + 5] = 1;
  wa = 3; wb = -3; wc = -1; wd = -2; we = 7; wf = 2; wg = 1; wh = -1;

  niters = 0; wx = -100;
  run_block (witer3, &c1, 3, -3, -1);
  for (wi = 3; wi > -3; wi--) for (wj = -2 * wi + 7; wj > 2 * wi + 1; wj--) wx = wi * 1024 + (wj & 1023);
  if (wi != -3 || wj != -3 || wx != -1026 || niters != 32) abort ();
  niters = 0; wx = -100;
  run_block (witer3, &c2, 3, -3, -1);
  for (wi = 3; wi > -3; wi--) for (wj = -2 * wi + 7; wj > 2 * wi + 1; wj--) wx = wi * 1024 + (wj & 1023);
  if (wi != -3 || wj != -3 || wx != -1026 || niters != 32) abort ();
  for (wi = 3; wi > -3; wi--)
    for (wj = -2 * wi + 7; wj > 2 * wi + 1; wj--)
      if (w[wi + 5][wj + 5] == 3) w[wi + 5][wj + 5] = 0; else abort ();

  for (wi = 3; wi > -3; wi--)
    for (wj = 2 * wi + 7; wj > -2 * wi + 1; wj--)
      w[wi + 5][wj + 5] = 1;
  wa = 3; wb = -3; wc = -1; wd = 2; we = 7; wf = -2; wg = 1; wh = -1;

  niters = 0; wx = -100;
  run_block (witer4, &c1, 3, -3, -1);
  for (wi = 3; wi > -3; wi--) for (wj = 2 * wi + 7; wj > -2 * wi + 1; wj--) wx = wi * 1024 + (wj & 1023);
  if (wx != -1020 || niters != 50) abort ();
  niters = 0; wx = -100;
  run_block (witer4, &c2, 3, -3, -1);
  for (wi = 3; wi > -3; wi--) for (wj = 2 * wi + 7; wj > -2 * wi + 1; wj--) wx = wi * 1024 + (wj & 1023);
  if (wx != -1020 || niters != 50) abort ();
  for (wi = 3; wi > -3; wi--)
    for (wj = 2 * wi + 7; wj > -2 * wi + 1; wj--)
      if (w[wi + 5][wj + 5] == 3) w[wi + 5][wj + 5] = 0; else abort ();

  for (wi = 6; wi > -6; wi--)
    for (wj = 2 * wi + 7; wj <= -2 * wi + 1; wj++)
      w[wi + 5][wj + 5] = 1;
  wa = 6; wb = -6; wc = -1; wd = 2; we = 7; wf = -2; wg = 2; wh = 1;

  niters = 0; wx = -100;
  run_block (witer5, &c1, 6, -6, -1);
  for (wi = 6; wi > -6; wi--) for (wj = 2 * wi + 7; wj <= -2 * wi + 1; wj++) wx = wi * 1024 + (wj & 1023);
  if (wi != -6 || wj != 12 || wx != -5109 || niters != 36) abort ();
  niters = 0; wx = -100;
  run_block (witer5, &c2, 6, -6, -1);
  for (wi = 6; wi > -6; wi--) for (wj = 2 * wi + 7; wj <= -2 * wi + 1; wj++) wx = wi * 1024 + (wj & 1023);
  if (wi != -6 || wj != 12 || wx != -5109 || niters != 36) abort ();
  for (wi = 6; wi > -6; wi--)
    for (wj = 2 * wi + 7; wj <= -2 * wi + 1; wj++)
      if (w[wi + 5][wj + 5] == 3) w[wi + 5][wj + 5] = 0; else abort ();

  for (wi = 6; wi > -6; wi -= 2)
    for (wj = -2 * wi + 7; wj <= 2 * wi + 1; wj++)
      w[wi + 5][wj + 5] = 1;
  wa = 6; wb = -6; wc = -2; wd = -2; we = 7; wf = 2; wg = 2; wh = 1;

  niters = 0; wx = -100;
  run_block (witer6, &c1, 6, -6, -2);
  for (wi = 6; wi > -6; wi -= 2) for (wj = -2 * wi + 7; wj <= 2 * wi + 1; wj++) wx = wi * 1024 + (wj & 1023);
  if (wx != 2053 || niters != 33) abort ();
  niters = 0; wx = -100;
  run_block (witer6, &c2, 6, -6, -2);
  for (wi = 6; wi > -6; wi -= 2) for (wj = -2 * wi + 7; wj <= 2 * wi + 1; wj++) wx = wi * 1024 + (wj & 1023);
  if (wx != 2053 || niters != 33) abort ();
  for (wi = 6; wi > -6; wi -= 2)
    for (wj = -2 * wi + 7; wj <= 2 * wi + 1; wj++)
      if (w[wi + 5][wj + 5] == 3) w[wi + 5][wj + 5] = 0; else abort ();

  free (niters_priv);
  return 0;
}
