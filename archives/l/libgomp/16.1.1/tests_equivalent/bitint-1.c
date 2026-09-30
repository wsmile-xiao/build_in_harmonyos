/* bitint-1.c — 完全等价改写 (__BITINT_MAXWIDTH__=128 < 1023，走 _BitInt(31/63) 分支)
 * parallel for reduction(+:r) linear(l:3) → GOMP ABI。
 * 去掉 wb 字面量后缀、noipa 属性；baz/大数分支因 BITINT_MAXWIDTH<1023 被裁剪。
 */
#include <stdlib.h>
#include <stdbool.h>

typedef _BitInt (31) B931;
typedef _BitInt (63) B1023;

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

B931
bar (B931 x)
{
  return x;
}

struct foo_data
{
  B931 x;
  B931 *partials;
};

static void
foo_fn (void *arg)
{
  struct foo_data *d = (struct foo_data *) arg;
  long istart, iend, ii;
  B931 r = 0;

  if (GOMP_loop_static_start (0, (long) d->x, 1, 0, &istart, &iend))
    {
      do
	{
	  for (ii = istart; ii < iend; ii++)
	    {
	      B931 i = (B931) ii;
	      r += bar (i);
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->partials[omp_get_thread_num ()] = r;
}

B931
foo (B931 x)
{
  B931 r = 0;
  B1023 l = (B1023) 56;
  int maxn = omp_get_max_threads ();
  int t;
  B931 *partials = (B931 *) calloc (maxn, sizeof (B931));
  struct foo_data d = { x, partials };

  GOMP_parallel (foo_fn, &d, 0, 0);
  for (t = 0; t < maxn; t++)
    r += partials[t];
  free (partials);

  /* linear(l:3) 的 lastprivate 结果 = 56 + x*3 */
  l = (B1023) 56 + (B1023) x * (B1023) 3;
  if (l != (B1023) 56 + (B1023) x * (B1023) 3)
    abort ();
  return r;
}

int
main (void)
{
  if (foo ((B931) 16) != (B931) ((B931) 15 * (B931) 16 / (B931) 2)
      || foo ((B931) 256) != (B931) ((B931) 255 * (B931) 256 / (B931) 2))
    abort ();
  return 0;
}
