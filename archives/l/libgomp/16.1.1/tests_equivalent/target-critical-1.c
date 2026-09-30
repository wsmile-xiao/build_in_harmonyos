/* { dg-do run } */
#include <omp.h>
#include <stdlib.h>
#include <stdbool.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_loop_static_start (long, long, long, long, long *, long *);
bool GOMP_loop_static_next (long *, long *);
void GOMP_loop_end (void);
void GOMP_critical_start (void);
void GOMP_critical_end (void);

#define N 2000

struct foo_ctx { int *A; int *nthreads; };

static void
foo_par (void *d)
{
  struct foo_ctx *c = d;
  long istart, iend;
  int i;
  /* #pragma omp master */
  if (omp_get_thread_num () == 0)
    *(c->nthreads) = omp_get_num_threads ();
  /* #pragma omp for */
  if (GOMP_loop_static_start (0, N, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    c->A[i] = 0;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  /* #pragma omp critical */
  GOMP_critical_start ();
  for (i = 0; i < N; i++)
    c->A[i]++;
  GOMP_critical_end ();
}

int
foo (void)
{
  int A[N];
  int i, nthreads;
  int res = 0;
  struct foo_ctx c = { A, &nthreads };
  GOMP_parallel (foo_par, &c, 0, 0);
  for (i = 0; i < N; i++)
    if (A[i] != nthreads)
      res = 1;
  return res;
}

int
main ()
{
  int res1, res2;
  /* target map(from:res1,res2): host fallback */
  {
    int B[N];
    int i, nthreads;
    struct foo_ctx c = { B, &nthreads };

    res1 = foo ();

    GOMP_parallel (foo_par, &c, 0, 0);

    res2 = 0;
    for (i = 0; i < N; i++)
      if (B[i] != nthreads)
	res2 = 1;
  }

  if (res1 || res2)
    abort ();

  return 0;
}
