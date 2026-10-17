/* Equiv-rewrite of upstream loop-26.c.
 * `parallel { for collapse(N) reduction(+:niters) }` with pointer inner loops:
 * the outer loop is distributed via GOMP_loop_static; the pointer inner loops
 * are expressed as integer indices (each tuple touches a distinct v[] element).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

signed char v[5][7][9][21][4][42][3];

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

static void iter_c7 (void *ctx, long i_) { struct c *c = ctx; int j, k, l, m, n, o, t = omp_get_thread_num ();
  for (j = 0; j < 7; j++)
    for (k = 0; k < 9; k++)
      for (l = j; l < j + 5; l++)
	for (m = 0; m < 4; m++)
	  for (n = 0; n < l - 2; n++)
	    for (o = 0; o < 3; o++)
	      {
		niters_priv[t]++;
		if (i_ < 0 || i_ >= 5 || j < 0 || j >= 7 || k < 0 || k >= 9
		    || l < 0 || l >= j + 5 || m < 0 || m >= 4
		    || n < 0 || n >= l - 2 || o < 0 || o >= 3)
		  abort ();
		if (v[i_][j][k][l][m][n][o] != c->expected)
		  abort ();
		v[i_][j][k][l][m][n][o]++;
	      } }

static void iter_c5 (void *ctx, long i_) { struct c *c = ctx; int j, l, n, o, t = omp_get_thread_num ();
  for (j = 0; j < 7; j++)
    for (l = j; l < j + 5; l++)
      for (n = 0; n <= l - 3; n++)
	for (o = 0; o < 3; o++)
	  {
	    niters_priv[t]++;
	    if (i_ < 0 || i_ >= 5 || j < 0 || j >= 7 || l < j || l >= j + 5
		|| n < 0 || n >= l - 2 || o < 0 || o >= 3)
	      abort ();
	    if (v[i_][j][0][l][0][n][o] != c->expected)
	      abort ();
	    v[i_][j][0][l][0][n][o]++;
	  } }

static void iter_c3 (void *ctx, long j_) { struct c *c = ctx; int l, n, t = omp_get_thread_num ();
  for (l = j_; l <= j_ + 4; l++)
    for (n = 0; n <= l - 3; n++)
      {
	niters_priv[t]++;
	if (j_ < 0 || j_ >= 7 || l < j_ || l >= j_ + 5 || n < 0 || n >= l - 2)
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
	for (l = j; l < 5 + j; l++)
	  for (m = 7; m < 11; m++)
	    for (n = 0; n < l - 2; n++)
	      for (o = 0; o < 3; o++)
		v[i][j][k][l][m - 7][n][o] = 1;

  niters = 0; run_block (iter_c7, &c1, 0, 5, 1);
  if (niters != 58860) abort ();
  niters = 0; run_block (iter_c7, &c2, 0, 5, 1);
  if (niters != 58860) abort ();
  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (k = 0; k < 9; k++)
	for (l = j; l < 5 + j; l++)
	  for (m = 7; m < 11; m++)
	    for (n = 0; n < l - 2; n++)
	      for (o = 0; o < 3; o++)
		if (v[i][j][k][l][m - 7][n][o] != 3)
		  abort ();

  niters = 0; run_block (iter_c5, &c3, 0, 5, 1);
  if (niters != 1635) abort ();
  niters = 0; run_block (iter_c5, &c4, 0, 5, 1);
  if (niters != 1635) abort ();
  for (i = 0; i < 5; i++)
    for (j = 0; j < 7; j++)
      for (l = j; l < j + 5; l++)
	for (n = 0; n < l - 2; n++)
	  for (o = 0; o < 3; o++)
	    if (v[i][j][0][l][0][n][o] != 5)
	      abort ();

  niters = 0; run_block (iter_c3, &c5, 0, 7, 1);
  if (niters != 109) abort ();
  niters = 0; run_block (iter_c3, &c6, 0, 7, 1);
  if (niters != 109) abort ();
  for (j = 0; j < 7; j++)
    for (l = j; l < j + 5; l++)
      for (n = 0; n < l - 2; n++)
	if (v[0][j][0][l][0][n][0] != 7)
	  abort ();

  free (niters_priv);
  return 0;
}
