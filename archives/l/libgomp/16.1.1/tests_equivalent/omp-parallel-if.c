/* Equiv-rewrite of upstream omp-parallel-if.c.
 * #pragma omp parallel if(...) num_threads(...)  -> GOMP_parallel (or serial).
 */
#include <omp.h>
extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

int foo (void) { return 10; }

static void body (void *data)
{
  int *A = (int *)data;
  *A = omp_get_num_threads ();
}

int main (void)
{
  int A = 0;
  /* parallel if(foo()>10): foo()==10, condition false -> serial */
  body (&A);
  if (A != 1) abort ();

  /* parallel if(foo()==10) num_threads(3) */
  GOMP_parallel (body, &A, 3, 0);
  if (A != 3) abort ();

  /* parallel if(foo()==10) num_threads(foo())=10 */
  GOMP_parallel (body, &A, 10, 0);
  if (A != 10) abort ();

  return 0;
}
