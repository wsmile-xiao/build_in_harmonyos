/* Equiv-rewrite of upstream simd-2.c.
 * #pragma omp simd / for simd / parallel-for-simd are vectorization hints (or
 * order-independent reductions), so the serial body is fully equivalent; all
 * #pragma omp lines are removed.
 */
/* { dg-do run } */
/* { dg-additional-options "-msse2" { target sse2_runtime } } */
/* { dg-additional-options "-mavx" { target avx_runtime } } */

extern void abort ();
__UINTPTR_TYPE__ arr[1027];

__attribute__((noinline, noclone)) void
foo ()
{
  int i, v;
  for (i = 0; i < 1027; i++)
    arr[i] = (__UINTPTR_TYPE__) &v;
}

int
main ()
{
  int i, j, cnt = 0;
  __UINTPTR_TYPE__ arr2[16];
  foo ();
  for (i = 0; i < 1027; i++)
    {
      for (j = 0; j < cnt; j++)
	if (arr[i] == arr2[j])
	  break;
      if (j != cnt)
	continue;
      if (cnt == 16)
	abort ();
      arr2[cnt++] = arr[i];
    }
  return 0;
}
