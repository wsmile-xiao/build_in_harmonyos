/* Equiv-rewrite of upstream loop-17.c.
 * `#pragma omp parallel { #pragma omp for collapse(N) reduction(+:niters) }`:
 * the OUTER loop is distributed via GOMP_loop_static and the inner loops run
 * to completion (each 7-tuple touches a distinct v[] element, so no races).
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

int
main ()
{
  struct c c1 = { 1 }, c2 = { 2 }, c3 = { 3 }, c4 = { 4 }, c5 = { 5 }, c6 = { 6 };
  int i, j, k, l, m, n, o;

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

  niters = 0;
  run_block (iter7, &c1, 0, 5, 1);
  if (niters != 117180) abort ();

  niters = 0;
  run_block (iter7, &c2, 0, 5, 1);
  if (niters != 117180) abort ();

  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (k = 0; k < 9; k++)
	for (l = 2 * j; l < 3 * j; l++)
	  for (m = 7; m < 11; m++)
	    for (n = l; n < 2 * l; n++)
	      for (o = 0; o < 3; o++)
		if (v[i][j][k][l][m - 7][n][o] != 3)
		  abort ();

  niters = 0;
  run_block (iter5, &c3, 0, 5, 1);
  if (niters != 3255) abort ();

  niters = 0;
  run_block (iter5, &c4, 0, 5, 1);
  if (niters != 3255) abort ();

  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (l = 2 * j; l < 3 * j; l++)
	for (n = l; n < 2 * l; n++)
	  for (o = 0; o < 3; o++)
	    if (v[i][j][0][l][0][n][o] != 5)
	      abort ();

  niters = 0;
  run_block (iter3, &c5, 0, 7, 1);
  if (niters != 217) abort ();

  niters = 0;
  run_block (iter3, &c6, 0, 7, 1);
  if (niters != 217) abort ();

  for (j = 0; j < 7; j++)
    for (l = 2 * j; l < 3 * j; l++)
      for (n = l; n < 2 * l; n++)
	if (v[0][j][0][l][0][n][0] != 7)
	  abort ();

  free (niters_priv);
  return 0;
}
