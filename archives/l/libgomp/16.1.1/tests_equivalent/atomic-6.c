/* Equiv-rewrite of upstream atomic-6.c. */
#include <stdlib.h>
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

union { unsigned long long l; double d; } u = { .l = 0x7ff0000000072301ULL };

int __attribute__((noinline))
do_test (void)
{
  GOMP_atomic_start (); u.d += 1.0L; GOMP_atomic_end ();
  return 0;
}

int
main (void)
{
  do_test ();
  return 0;
}
