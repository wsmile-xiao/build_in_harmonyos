/* Equiv-rewrite of upstream loop-3.c.
 * Orphaned `#pragma omp for lastprivate(i)` runs with a team of one thread,
 * so it is semantically a plain serial loop; `i` ends at its sequential
 * exit value (10) which is what lastprivate reproduces.
 */
extern void abort (void);

volatile int count;
static int test(void)
{
  return ++count > 0;
}

int i;

int main()
{
  for (i = 0; i < 10; ++i)
    {
      if (test())
	continue;
      abort ();
    }
  if (i != count)
    abort ();
  return 0;
}
