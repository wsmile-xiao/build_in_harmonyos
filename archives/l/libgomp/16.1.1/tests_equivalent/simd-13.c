/* Equiv-rewrite of upstream simd-13.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

int
main ()
{
  int k = 0, i, s = 0;
  for (i = 0; i < 128; i++)
    {
      k = k + 3;
      s = s + k;
    }
  if (s != 128 * 129 / 2 * 3) __builtin_abort ();
  return 0;
}
