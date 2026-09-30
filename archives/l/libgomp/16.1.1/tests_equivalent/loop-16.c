/* Equiv-rewrite of upstream loop-16.c.
 * Orphaned `#pragma omp for lastprivate(i)` = single-thread worksharing loop,
 * so a plain serial loop is fully equivalent (i ends at 10, count == 10).
 */
extern void abort (void);

volatile int count;
static int test (void)
{
  return ++count > 0;
}

int i;

int
main ()
{
  for (i = 0; i < 10; ++i)
    {
      int *p = &i;
      (void) p;
      if (test ())
	continue;
      abort ();
    }
  if (i != count)
    abort ();
  return 0;
}
