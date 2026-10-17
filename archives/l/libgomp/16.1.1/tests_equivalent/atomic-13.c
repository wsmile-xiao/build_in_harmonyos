/* Equiv-rewrite of upstream atomic-13.c: long long atomic read/write/capture. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

long long l, m;
int i, j;

void
foo (void)
{
  GOMP_atomic_start (); i = l; GOMP_atomic_end ();
  GOMP_atomic_start (); m = j; GOMP_atomic_end ();
  if (i != 77 || m != 88)
    abort ();
  GOMP_atomic_start (); l = 1 + i + 6 * 1; GOMP_atomic_end ();
  GOMP_atomic_start (); j = 170 - 170 + m + 1 * 7; GOMP_atomic_end ();
  GOMP_atomic_start (); i = l += 4; GOMP_atomic_end ();
  GOMP_atomic_start (); m = j += 4; GOMP_atomic_end ();
  if (i != 88 || m != 99)
    abort ();
  GOMP_atomic_start ();
  {
    i = l;
    l += 4;
  }
  GOMP_atomic_end ();
  GOMP_atomic_start ();
  {
    m = j;
    j += 4;
  }
  GOMP_atomic_end ();
  if (i != 88 || m != 99)
    abort ();
  GOMP_atomic_start ();
  {
    l += 4;
    i = l;
  }
  GOMP_atomic_end ();
  GOMP_atomic_start ();
  {
    j += 4;
    m = j;
  }
  GOMP_atomic_end ();
  if (i != 96 || m != 107)
    abort ();
}

int
main ()
{
  l = 77;
  j = 88;
  foo ();
  return 0;
}
