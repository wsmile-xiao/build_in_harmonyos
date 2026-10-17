/* Equiv-rewrite of upstream nestedfn-1.c.
 * GNU nested function -> static fn + pointer arg.
 * #pragma omp parallel shared/private/firstprivate/reduction(||)/barrier
 * -> GOMP_parallel + GOMP_barrier + manual || reduction.
 */
#include <omp.h>
#include <stdlib.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);

#define MAXT 128

struct data {
  int *a;          /* shared a */
  int c;           /* firstprivate c */
  int *l_priv;     /* reduction (||:l) per-thread copies */
};

static void body (void *p)
{
  struct data *d = (struct data *) p;
  int tn = omp_get_thread_num ();
  int b;            /* private b (uninitialized) */
  int c = d->c;     /* firstprivate c */
  int l = 0;        /* reduction (||) neutral = 0 */

  if (*d->a != 1 || c != 3) l = 1;
  GOMP_barrier ();
  if (tn == 0) { *d->a = 4; b = 5; c = 6; }
  GOMP_barrier ();
  if (tn == 1)
    {
      if (*d->a != 4 || c != 3) l = 1;
      *d->a = 7; b = 8; c = 9;
    }
  else if (omp_get_num_threads () == 1)
    *d->a = 7;
  GOMP_barrier ();
  if (tn == 0)
    if (*d->a != 7 || b != 5 || c != 6) l = 1;
  GOMP_barrier ();
  if (tn == 1)
    if (*d->a != 7 || b != 8 || c != 9) l = 1;

  d->l_priv[tn] = l;
}

static void foo (int *a, int c)
{
  int l = 0;
  int l_priv[MAXT] = {0};
  struct data d = { a, c, l_priv };
  int t;
  GOMP_parallel (body, &d, 2, 0);
  for (t = 0; t < MAXT; t++)
    l = l || l_priv[t];
  if (l)
    abort ();
}

int main (void)
{
  int a = 1, c = 3;   /* b is private-only in the region, not observed outside */
  foo (&a, c);
  if (a != 7)
    abort ();
  return 0;
}
