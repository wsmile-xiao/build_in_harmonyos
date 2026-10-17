/* Equiv-rewrite of upstream simd-5.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

extern void abort ();
int a[1024] __attribute__((aligned (32))) = { 1 };
struct S { int s; };

__attribute__((noinline, noclone)) int
foo (void)
{
  int i, u = 0, q = 0;
  struct S s, t;
  s.s = 0; t.s = 0;
  for (i = 0; i < 1024; i++)
    {
      int x = a[i];
      s.s += x;
      t.s += x;
      u += x;
      q++;
    }
  if (t.s != s.s || u != s.s || q != 1024)
    abort ();
  return s.s;
}

int
main ()
{
  int i;
  for (i = 0; i < 1024; i++)
    a[i] = (i & 31) + (i / 128);
  int s = foo ();
  if (s != 19456)
    abort ();
  return 0;
}
