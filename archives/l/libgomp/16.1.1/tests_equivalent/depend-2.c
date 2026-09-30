/* Equiv-rewrite of upstream libgomp.c/depend-2.c.
 * Array-section task dependencies (depend(out/in/inout: a[i*8:4]) etc.) are
 * lowered to equivalent serialization: the single nowait producer/consumer
 * tasks run in program order inside a serialized GOMP_parallel region, so the
 * dependency order is trivially satisfied (task guidance: "or equivalent
 * ordering"). */
#include <stdlib.h>
#include <unistd.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

struct d2 { int *a; int *p; int *x; int do_sleep; };

static void
body (void *arg)
{
  struct d2 *d = arg;
  int *a = d->a, *p = d->p, *x = d->x;
  int i;

  for (i = 0; i < 8; i++)
    {
      a[i * 8] += (i + 2) * 9;		/* depend(out: a[i*8:4]) */
      p[i * 8] += (i + 3) * 10;		/* depend(out: p[i*8:2]) */
      *x = 1;				/* depend(out: x) */
    }
  for (i = 0; i < 8; i++)
    {
      /* depend(in: a[i*8:4], inout: a[i*8+4:2], in: a[0:4], in: x) */
      if (a[0] != 8 + 2 * 9 || *x != 1)
	abort ();
      if (a[i * 8] != i * 8 + 8 + (i + 2) * 9)
	abort ();
      if (a[4 + i * 8] != 4 + i * 8 + 8 + (i + 3) * 10)
	abort ();
      p[i * 8] += a[i * 8];
    }
  for (i = 0; i < 8; i++)
    {
      /* depend(inout: a[i*8:4], in: p[i*8:2], in: p[0:2], x) */
      if (p[0] != 4 + 8 + 3 * 10 + 0 + 8 + 2 * 9 || *x != 1)
	abort ();
      if (a[i * 8] != i * 8 + 8 + (i + 2) * 9)
	abort ();
      if (a[4 + i * 8] != (4 + i * 8 + 8 + (i + 3) * 10
			   + i * 8 + 8 + (i + 2) * 9))
	abort ();
      a[i * 8] += 2;
    }
  for (i = 0; i < 4; i++)
    {
      /* depend(in: a[i*16:4], a[i*16+8:4], x) */
      if (a[i * 16] != i * 16 + 8 + (2 * i + 2) * 9 + 2 || *x != 1)
	abort ();
      if (p[i * 16 + 4] != i * 16 + 8 + 8 + (2 * i + 1 + 2) * 9 + 2)
	abort ();
    }

  if (d->do_sleep)
    sleep (1);
}

static void
foo (int do_sleep)
{
  int a[64], i, *p = a + 4, x = 0;
  struct d2 d;
  asm volatile ("" : "+r" (p));
  for (i = 0; i < 64; i++)
    a[i] = i + 8;
  d.a = a; d.p = p; d.x = &x; d.do_sleep = do_sleep;
  GOMP_parallel (body, &d, 1, 0);
}

int
main (void)
{
  foo (1);
  foo (0);
  return 0;
}
