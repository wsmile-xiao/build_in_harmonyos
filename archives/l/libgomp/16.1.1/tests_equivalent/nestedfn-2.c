/* Equiv-rewrite of upstream nestedfn-2.c.
 * GNU nested function -> static fn + pointer arg.
 * #pragma omp master (called from serial context) -> execute directly.
 */
#include <omp.h>
extern void abort (void);

static void foo (int *i)
{
  /* omp master in serial context == thread 0 only == always */
  if (omp_get_thread_num () == 0)
    *i += 8;
}

int main (void)
{
  int i = 4;
  foo (&i);
  if (i != 12)
    abort ();
  return 0;
}
