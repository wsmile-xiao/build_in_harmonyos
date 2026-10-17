/* Equiv-rewrite of upstream pr24455-1.c (dg-do compile; requires tls).
 * Original only checks that `#pragma omp threadprivate (i)` on an extern TLS
 * declaration compiles. On OHOS clang the pragma is ignored, so we model the
 * thread-private storage with `__thread` and make it a runnable program.
 */
__thread int i;

int
main (void)
{
  i = 42;
  if (i != 42)
    __builtin_abort ();
  return 0;
}
