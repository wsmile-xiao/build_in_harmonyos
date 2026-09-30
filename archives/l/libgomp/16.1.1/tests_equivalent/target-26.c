// { dg-additional-options "-Wno-deprecated-openmp" }
extern void abort (void);
#include <stdbool.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_single_start (void);

int a[4] = { 2, 3, 4, 5 }, *b;

struct ctx26 { int a[4]; int *b; int c[3]; int err; };

static void
par26 (void *d)
{
  struct ctx26 *in = d;
  /* firstprivate(a, b, c, err): thread-local copies */
  int la[4], lc[3], lerr;
  int *lb;
  for (int i = 0; i < 4; i++) la[i] = in->a[i];
  for (int i = 0; i < 3; i++) lc[i] = in->c[i];
  lerr = in->err;
  lb = lc; /* firstprivate pointer redirected to thread's c copy */

  if (GOMP_single_start ())
    {
      lb = lc + 1;
      la[0] = 11;
      la[2] = 13;
      lc[1] = 14;
      int d0 = 0;
      /* target map(to:a[0:3], b[d:2]) map(from:err): host fallback */
      lerr = la[0] != 11 || la[1] != 9 || la[2] != 13 || lb[0] != 14 || lb[1] != 8;
      if (lerr)
	abort ();
    }
}

int
main ()
{
  int err;
  int c[3] = { 6, 7, 8 };
  b = c;
  /* target map(to:a[0:2], b[0:2]) map(from:err) */
  err = a[0] != 2 || a[1] != 3 || a[2] != 4 || a[3] != 5 || b[0] != 6 || b[1] != 7;
  if (err)
    abort ();
  a[1] = 9;
  a[2] = 10;
  /* target map(always,to:a[1:2]) map(from:err) */
  err = a[0] != 2 || a[1] != 9 || a[2] != 10 || a[3] != 5;
  if (err)
    abort ();
  {
    struct ctx26 ctx;
    for (int i = 0; i < 4; i++) ctx.a[i] = a[i];
    ctx.b = b;
    for (int i = 0; i < 3; i++) ctx.c[i] = c[i];
    ctx.err = err;
    GOMP_parallel (par26, &ctx, 2, 0);
  }
  return 0;
}
