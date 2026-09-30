/* shared-3.c — 完全等价改写
 * 原: #pragma omp parallel { if (p != &x) abort(); }  p、x 共享。
 */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

struct d
{
  int x;
  int *p;
};

static void
fn (void *arg)
{
  struct d *d = (struct d *) arg;
  if (d->p != &d->x)
    abort ();
}

int
main (void)
{
  struct d d;
  d.p = &d.x;
  GOMP_parallel (fn, &d, 0, 0);
  return 0;
}
