/* Equiv-rewrite of upstream simd-10.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

int s = 0, i, u;

void
foo ()
{
  for (i = 0; i < 128; i++)
    {
      s++;
      u = i;
    }
  if (i != 128 || s != 128 || u != 127)
    __builtin_abort ();
}

int
main ()
{
  foo ();
  return 0;
}
