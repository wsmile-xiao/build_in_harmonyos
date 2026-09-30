/* Equiv-rewrite of upstream nestedfn-3.c.
 * GNU nested functions foo()/bar() reading outer i -> static fns + const int*.
 * parallel if/num_threads/reduction(|) -> GOMP_parallel + manual | reduction.
 * master/single in serial context -> execute directly.
 * atomic -> GOMP_atomic_start/end.
 */
#include <omp.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define MAXT 128

static int foo (const int *i) { return *i == 6; }
static int bar (const int *i) { return *i - 3; }

static int l_priv[MAXT];

/* body expecting omp_get_num_threads()==expect; sets l_priv[tn]=1 on mismatch */
struct b_data { int expect; };
static void body (void *p)
{
  struct b_data *d = (struct b_data *) p;
  int tn = omp_get_thread_num ();
  int l = 0;
  if (omp_get_num_threads () != d->expect)
    l = 1;
  l_priv[tn] = l;
}

int main (void)
{
  int i = 5, l = 0;
  int t;

  omp_set_dynamic (0);

  /* region 1: parallel if(foo()) num_threads(bar()) reduction(|:l); i==5 -> 1 thread */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct b_data d = { 1 };
    if (foo (&i)) GOMP_parallel (body, &d, bar (&i), 0);
    else          GOMP_parallel (body, &d, 1, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  i++;

  /* region 2: i==6 -> 3 threads */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct b_data d = { 3 };
    if (foo (&i)) GOMP_parallel (body, &d, bar (&i), 0);
    else          GOMP_parallel (body, &d, 1, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  i++;

  /* #pragma omp master (serial context) */
  if (omp_get_thread_num () == 0)
    if (bar (&i) != 4)
      abort ();

  /* #pragma omp single (serial context) */
  {
    if (foo (&i))
      abort ();
    i--;
    if (! foo (&i))
      abort ();
  }

  if (l)
    abort ();

  i = 8;
  /* #pragma omp atomic l += bar(); */
  GOMP_atomic_start ();
  l += bar (&i);
  GOMP_atomic_end ();

  if (l != 5)
    abort ();

  return 0;
}
