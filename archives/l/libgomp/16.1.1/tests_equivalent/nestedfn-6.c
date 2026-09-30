/* Equiv-rewrite of upstream nestedfn-6.c.
 * GNU nested fn nested() is declared but never called -> drop it.
 * #pragma omp parallel for lastprivate(i) -> GOMP_parallel + GOMP_loop_static_*;
 *   lastprivate value = sequential final loop var (start + N*incr), recorded as
 *   the max of each thread's final loop-variable value.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 128

int j;

struct lp_data {
  long start, end, incr;
  long *last_priv;   /* per-thread final loop-var value */
};

static void lp_body (void *p)
{
  struct lp_data *d = (struct lp_data *) p;
  int tn = omp_get_thread_num ();
  long iv;
  long istart, iend;
  d->last_priv[tn] = d->start;
  if (GOMP_loop_static_start (d->start, d->end, d->incr, 0, &istart, &iend))
    {
      do
	{
	  for (iv = istart; iv < iend; iv += d->incr)
	    ; /* empty body */
	}
      while (GOMP_loop_static_next (&istart, &iend));
      d->last_priv[tn] = iv;
    }
  GOMP_loop_end ();
}

static long lastprivate_of (long start, long end, long incr)
{
  long last_priv[MAXT];
  struct lp_data d = { start, end, incr, last_priv };
  long f;
  int t;
  for (t = 0; t < MAXT; t++)
    last_priv[t] = start;
  GOMP_parallel (lp_body, &d, 0, 0);
  f = last_priv[0];
  for (t = 1; t < MAXT; t++)
    if (last_priv[t] > f)
      f = last_priv[t];
  return f;
}

int main (void)
{
  int i;
  /* parallel for lastprivate(i): i=0; i<50; i+=3; empty body -> i == 51 */
  i = (int) lastprivate_of (0, 50, 3);
  if (i != 51)
    abort ();
  /* parallel for lastprivate(j): j=-50; j<70; j+=7 -> j == 76 */
  j = (int) lastprivate_of (-50, 70, 7);
  if (j != 76)
    abort ();
  return 0;
}
