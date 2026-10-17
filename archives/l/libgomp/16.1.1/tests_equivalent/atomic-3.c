/* Equiv-rewrite of upstream atomic-3.c: parallel num_threads(4) + barrier + atomic. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

short e[64];
int g;
_Complex double d, f;
int num_threads;

struct data
{
  short *e;
  int *g;
  _Complex double *d;
  _Complex double *f;
  int *num_threads;
  int x;
  long long y;
};

static void
body (void *p)
{
  struct data *dd = (struct data *) p;
  int i;
  GOMP_barrier ();
  for (i = 0; i < 2400; i++)
    {
      if (i == 0)
	*dd->num_threads = omp_get_num_threads ();
      GOMP_atomic_start (); dd->e[0] += dd->x; GOMP_atomic_end ();
      GOMP_atomic_start (); dd->e[16] += dd->x; GOMP_atomic_end ();
      GOMP_atomic_start (); *dd->g += dd->y; GOMP_atomic_end ();
      GOMP_atomic_start (); __real__ (*(dd->d)) += dd->x; GOMP_atomic_end ();
      GOMP_atomic_start (); __imag__ (*(dd->f)) += dd->x; GOMP_atomic_end ();
    }
}

__attribute__((noinline)) void
foo (int x, long long y)
{
  struct data dd;
  dd.e = e;
  dd.g = &g;
  dd.d = &d;
  dd.f = &f;
  dd.num_threads = &num_threads;
  dd.x = x;
  dd.y = y;
  GOMP_parallel (body, &dd, 4, 0);
}

int
main (void)
{
  int i;
  foo (3, 3LL);
  if (g != 3 * 2400 * num_threads
      || __real__ d != g || __imag__ d != 0
      || __real__ f != 0 || __imag__ f != g)
    abort ();
  for (i = 0; i < 64; i++)
    if (e[i] != ((i && i != 16) ? 0 : g))
      abort ();
  return 0;
}
