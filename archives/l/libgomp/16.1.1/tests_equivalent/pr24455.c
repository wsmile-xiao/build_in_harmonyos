/* Equiv-rewrite of upstream pr24455.c.
 *
 * Upstream failure cause: `extern int i; #pragma omp threadprivate(i)` with the
 * definition `int i;` in a separate additional source (pr24455-1.c) -> linking
 * pr24455.c alone yields "undefined symbol i".  Additionally, threadprivate needs
 * TLS which OHOS clang's (ignored) OpenMP path does not produce.
 *
 * Equivalent rewrite: define the storage and emulate threadprivate as a per-thread
 * copy indexed by thread number; on region entry every thread's copy is initialized
 * from the master thread's value (0). default(none) has no runtime effect.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);

#define MAXT 128
static int i_tls[MAXT];   /* threadprivate(i): per-thread copies */

static void body (void *p)
{
  int tn = omp_get_thread_num ();
  (void) p;
  i_tls[tn]++;             /* i++ on this thread's private copy */
  GOMP_barrier ();
  if (i_tls[tn] != 1)
    abort ();
}

int main (void)
{
  int t;
  /* i = 0 (initial thread's copy); copyin to all threads on region entry */
  for (t = 0; t < MAXT; t++)
    i_tls[t] = 0;
  GOMP_parallel (body, 0, 10, 0);
  return 0;
}
