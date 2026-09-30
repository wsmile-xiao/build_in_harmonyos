/* Equiv-rewrite of upstream simd-9.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

extern void abort ();
int a[32][32] __attribute__((aligned (32))) = { { 1 } };
struct S { int s; };

__attribute__((noinline, noclone)) int
foo (void)
{
  int i, j, u = 0;
  struct S s, t;
  s.s = 0; t.s = 0;
  for (i = 0; i < 32; i++)
    for (j = 0; j < 32; j++)
      {
	int *q = &i;
	int *r = &j;
	int x = a[i][j];
	s.s += x;
	t.s += x;
	u += x;
      }
  if (t.s != s.s || u != s.s || i != 32 || j != 32)
    abort ();
  return s.s;
}

__attribute__((noinline, noclone)) int
bar (void)
{
  int i, j, u = 0;
  struct S s, t;
  s.s = 0; t.s = 0;
  for (i = 0; i < 32; i++)
    for (j = 0; j < 32; j++)
      {
	int *q = &i;
	int *r = &j;
	int x = a[i][j];
	s.s += x;
	t.s += x;
	u += x;
      }
  if (t.s != s.s || u != s.s || i != 32 || j != 32)
    abort ();
  return s.s;
}

int
main ()
{
  int i, j;
  for (i = 0; i < 32; i++)
    for (j = 0; j < 32; j++)
      a[i][j] = j + (i / 4);
  int s = foo ();
  if (s != 19456)
    abort ();
  if (bar () != 19456)
    abort ();
  return 0;
}
