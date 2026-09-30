/* Equiv-rewrite of upstream loop-27.c.
 * The collapse(2) loops iterate over short* pointers into v[]; the outer
 * pointer loop is distributed by its integer index (via GOMP_loop_static) and
 * the inner pointer loop runs serially per outer iteration.  lastprivate(i,j,x)
 * is reproduced with a serial pointer dry-run.
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

int x;
short *i, *j;
int ii, jj;
short *volatile a;
short *volatile b;
volatile int c, e, f, g;
short *volatile d;
int k[11][20];
short v[84];

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

static void iter1 (void *ctx, long pi) { struct c1 *c = ctx; long pj;
  for (pj = 1; pj <= pi + 5; pj++)
    { if (pi < 1 || pi > 10 || pj < 1 || pj > pi + 5 || k[pi][pj] != c->expected) abort ();
      k[pi][pj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter2 (void *ctx, long pi) { struct c1 *c = ctx; long pj;
  for (pj = 0; pj < pi; pj++)
    { if (pi < 0 || pi >= 10 || pj < 0 || pj >= pi || k[pi][pj] != c->expected) abort ();
      k[pi][pj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter3 (void *ctx, long pi) { struct c1 *c = ctx; long pj;
  for (pj = pi + 1; pj < pi + 4; pj++)
    { if (pi < 0 || pi >= 10 || pj < pi + 1 || pj >= pi + 4 || k[pi][pj] != c->expected) abort ();
      k[pi][pj]++; niters_priv[omp_get_thread_num ()]++; } }

static void iter4 (void *ctx, long pi) { struct c1 *c = ctx; long pj;
  for (pj = 1; pj < pi + 1; pj++)
    { if (pi < 1 || pi >= 10 || pj < 1 || pj >= pi + 1 || k[pi][pj] != c->expected) abort ();
      k[pi][pj]++; niters_priv[omp_get_thread_num ()]++; } }

int
main ()
{
  struct c1 c1 = { 1 }, c2 = { 2 };

  nt = omp_get_max_threads ();
  if (nt < 1) nt = 1;
  niters_priv = (int *) calloc ((size_t) nt, sizeof (int));

  for (ii = 1; ii <= 10; ii++)
    for (jj = 1; jj <= ii + 5; jj++)
      k[ii][jj] = 1;
  a = &v[42 + 1]; b = &v[42 + 11]; c = 1; d = &v[42 + 1]; e = 6; f = 1;

  niters = 0; x = -100;
  run_block (iter1, &c1, 1, 11, 1);
  for (i = &v[42 + 1]; i <= &v[42 + 10]; i++) for (j = &v[42 + 1]; j <= i + 5; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 11] || j != &v[42 + 16] || x != 10255 || niters != 105) abort ();
  niters = 0; x = -100;
  run_block (iter1, &c2, 1, 11, 1);
  for (i = &v[42 + 1]; i <= &v[42 + 10]; i++) for (j = &v[42 + 1]; j <= i + 5; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 11] || j != &v[42 + 16] || x != 10255 || niters != 105) abort ();
  for (ii = 1; ii <= 10; ii++)
    for (jj = 1; jj <= ii + 5; jj++)
      if (k[ii][jj] == 3) k[ii][jj] = 0; else abort ();
  for (ii = 0; ii < 11; ii++)
    for (jj = 0; jj < 20; jj++)
      if (k[ii][jj] != 0) abort ();

  for (ii = 0; ii < 10; ii++)
    for (jj = 0; jj < ii; jj++)
      k[ii][jj] = 1;
  a = &v[42]; b = &v[42 + 10]; c = 1; d = &v[42]; e = 0; f = 1;

  niters = 0; x = -100;
  run_block (iter2, &c1, 0, 10, 1);
  for (i = &v[42]; i < &v[42 + 10]; i++) for (j = &v[42]; j < i; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 10] || j != &v[42 + 9] || x != 9224 || niters != 45) abort ();
  niters = 0; x = -100;
  run_block (iter2, &c2, 0, 10, 1);
  for (i = &v[42]; i < &v[42 + 10]; i++) for (j = &v[42]; j < i; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 10] || j != &v[42 + 9] || x != 9224 || niters != 45) abort ();
  for (ii = 0; ii < 10; ii++)
    for (jj = 0; jj < ii; jj++)
      if (k[ii][jj] == 3) k[ii][jj] = 0; else abort ();
  for (ii = 0; ii < 11; ii++)
    for (jj = 0; jj < 20; jj++)
      if (k[ii][jj] != 0) abort ();

  for (ii = 0; ii < 10; ii++)
    for (jj = ii + 1; jj < ii + 4; jj++)
      k[ii][jj] = 1;
  a = &v[42]; b = &v[42 + 10]; c = 1; e = 1; f = 1; g = -4;

  niters = 0; x = -100;
  run_block (iter3, &c1, 0, 10, 1);
  for (i = &v[42]; i < &v[42 + 10]; i++) for (j = i + 1; j < i + 4; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 10] || j != &v[42 + 13] || x != 9228 || niters != 30) abort ();
  niters = 0; x = -100;
  run_block (iter3, &c2, 0, 10, 1);
  for (i = &v[42]; i < &v[42 + 10]; i++) for (j = i + 1; j < i + 4; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 10] || j != &v[42 + 13] || x != 9228 || niters != 30) abort ();
  for (ii = 0; ii < 10; ii++)
    for (jj = ii + 1; jj < ii + 4; jj++)
      if (k[ii][jj] == 3) k[ii][jj] = 0; else abort ();
  for (ii = 0; ii < 11; ii++)
    for (jj = 0; jj < 20; jj++)
      if (k[ii][jj] != 0) abort ();

  for (ii = 1; ii < 10; ii += 2)
    for (jj = 1; jj < ii + 1; jj++)
      k[ii][jj] = 1;
  a = &v[42 + 1]; b = &v[42 + 10]; c = 2; d = &v[42 + 1]; e = 1; f = 1;

  niters = 0; x = -100;
  run_block (iter4, &c1, 1, 10, 2);
  for (i = &v[42 + 1]; i < &v[42 + 10]; i += 2) for (j = &v[42 + 1]; j < i + 1; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 11] || j != &v[42 + 10] || x != 9225 || niters != 25) abort ();
  niters = 0; x = -100;
  run_block (iter4, &c2, 1, 10, 2);
  for (i = &v[42 + 1]; i < &v[42 + 10]; i += 2) for (j = &v[42 + 1]; j < i + 1; j++) x = (i - &v[42]) * 1024 + ((j - &v[42]) & 1023);
  if (i != &v[42 + 11] || j != &v[42 + 10] || x != 9225 || niters != 25) abort ();
  for (ii = 1; ii < 10; ii += 2)
    for (jj = 1; jj < ii + 1; jj++)
      if (k[ii][jj] == 3) k[ii][jj] = 0; else abort ();
  for (ii = 0; ii < 11; ii++)
    for (jj = 0; jj < 20; jj++)
      if (k[ii][jj] != 0) abort ();

  free (niters_priv);
  return 0;
}
