/* Equiv-rewrite of upstream nestedfn-4.c.
 * GNU nested fns foo()/bar() reading i -> static fns + const int*.
 * parallel if/num_threads/reduction(|) -> GOMP_parallel + manual | reduction.
 * parallel for schedule(static,chunk) -> GOMP_parallel + GOMP_loop_static_*.
 */
#include <omp.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 128

static int foo (const int *i) { return *i == 6; }
static int bar (const int *i) { return *i - 3; }

static int l_priv[MAXT];

/* parallel if(foo) num_threads(2): body checks num_threads==expect, atomic l++ */
struct p_data { int *l; int expect; };
static void p_body (void *p)
{
  struct p_data *d = (struct p_data *) p;
  if (omp_get_num_threads () != d->expect)
    {
      GOMP_atomic_start ();
      (*d->l)++;
      GOMP_atomic_end ();
    }
}

/* parallel for schedule(static,chunk) num_threads(2) reduction(|:l) */
struct f_data { long end; long chunk; long split; };
static void f_body (void *p)
{
  struct f_data *d = (struct f_data *) p;
  int tn = omp_get_thread_num ();
  int l = 0;
  long j, istart, iend;
  if (GOMP_loop_static_start (0, d->end, 1, d->chunk, &istart, &iend))
    {
      do
	{
	  for (j = istart; j < iend; j++)
	    if (tn != (j >= d->split))
	      l++;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  l_priv[tn] = l;
}

/* parallel num_threads(4) reduction(|:l) */
struct r_data { const int *i; };
static void r5_body (void *p)
{
  struct r_data *d = (struct r_data *) p;
  int tn = omp_get_thread_num ();
  int l = 0;
  if (! foo (d->i) || bar (d->i) != 3)
    l++;
  l_priv[tn] = l;
}
static void r6_body (void *p)
{
  struct r_data *d = (struct r_data *) p;
  int tn = omp_get_thread_num ();
  int l = 0;
  if (foo (d->i) || bar (d->i) != 4)
    l++;
  l_priv[tn] = l;
}

int main (void)
{
  int i = 5, l = 0;
  int t;

  omp_set_dynamic (0);

  /* region 1: parallel if(foo()) num_threads(2); i==5 -> 1 thread */
  {
    struct p_data d = { &l, 1 };
    if (foo (&i)) GOMP_parallel (p_body, &d, 2, 0);
    else          GOMP_parallel (p_body, &d, 1, 0);
  }

  /* region 2: parallel for schedule(static, bar()) num_threads(2) reduction(|:l) */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct f_data d = { 4, bar (&i), 2 };
    GOMP_parallel (f_body, &d, 2, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  i++;

  /* region 3: i==6 -> 2 threads */
  {
    struct p_data d = { &l, 2 };
    if (foo (&i)) GOMP_parallel (p_body, &d, 2, 0);
    else          GOMP_parallel (p_body, &d, 1, 0);
  }

  /* region 4: parallel for schedule(static, bar()) num_threads(2) reduction(|:l) */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct f_data d = { 6, bar (&i), 3 };
    GOMP_parallel (f_body, &d, 2, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  /* region 5: parallel num_threads(4) reduction(|:l); i==6 */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct r_data d = { &i };
    GOMP_parallel (r5_body, &d, 4, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  i++;

  /* region 6: parallel num_threads(4) reduction(|:l); i==7 */
  memset (l_priv, 0, sizeof l_priv);
  {
    struct r_data d = { &i };
    GOMP_parallel (r6_body, &d, 4, 0);
  }
  for (t = 0; t < MAXT; t++) l |= l_priv[t];

  if (l)
    abort ();
  return 0;
}
