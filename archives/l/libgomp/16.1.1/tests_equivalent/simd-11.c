/* Equiv-rewrite of upstream simd-11.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

int s = 0, i, j, u;

void
foo ()
{
  for (i = 0; i < 16; i++)
    for (j = 0; j < 16; j++)
      {
	s++;
	u = i + j;
      }
  if (i != 16 || j != 16 || s != 256 || u != 30)
    __builtin_abort ();
}

int
main ()
{
  foo ();
  return 0;
}
