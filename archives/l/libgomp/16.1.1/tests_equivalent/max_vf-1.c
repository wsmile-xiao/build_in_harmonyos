/* max_vf-1.c — 完全等价改写 (dg-do link，host-only)
 * target parallel for simd / parallel for simd → host 上 parallel for 降级。
 */
#include <stdbool.h>
#include <stddef.h>

#define N 1024
int a[N], b[N], c[N];

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern bool GOMP_loop_dynamic_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_dynamic_next (long *, long *);
extern void GOMP_loop_end (void);

static void
f2_fn (void *arg)
{
  long istart, iend;
  int i;
  if (GOMP_loop_static_start (0, N, 1, 7, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    a[i] = b[i] + c[i];
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

void
f2 (void)
{
  GOMP_parallel (f2_fn, NULL, 0, 0);
}

struct f3d
{
  int *a, *b, *c;
};

static void
f3_fn (void *arg)
{
  struct f3d *d = (struct f3d *) arg;
  long istart, iend;
  int i;
  if (GOMP_loop_dynamic_start (0, N, 1, 7, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    d->a[i] = d->b[i] + d->c[i];
	}
      while (GOMP_loop_dynamic_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

void
f3 (int *a, int *b, int *c)
{
  struct f3d d = { a, b, c };
  GOMP_parallel (f3_fn, &d, 0, 0);
}

int
main (void)
{
  return 0;
}
