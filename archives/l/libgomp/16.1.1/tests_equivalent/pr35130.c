/* Equiv-rewrite of upstream pr35130.c.
 * GNU nested fns -> static fns + pointer args (arrays passed as int*).
 * #pragma omp parallel for -> GOMP_parallel + GOMP_loop_static_*.
 * #pragma omp parallel/single -> GOMP_parallel + GOMP_single_start + GOMP_barrier.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_single_start (void);
extern void GOMP_barrier (void);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

static void f1_nested (int *a, int x) { a[x] = 42; }

struct f1_data { int *a; };
static void f1_body (void *p)
{
  struct f1_data *d = (struct f1_data *) p;
  long k, istart, iend;
  if (GOMP_loop_static_start (0, 4, 1, 0, &istart, &iend))
    {
      do
	{
	  for (k = istart; k < iend; k++)
	    f1_nested (d->a, (int) k);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void f1 (void)
{
  int a[4], k;
  struct f1_data d = { a };
  for (k = 0; k < 4; k++)
    a[k] = 0;
  GOMP_parallel (f1_body, &d, 0, 0);
  if (a[0] != 42 || a[1] != 42 || a[2] != 42 || a[3] != 42)
    abort ();
}

static void f2_nested2 (int *a, int x) { a[x] = 42; }
struct f2_data { int *a; };
static void f2_body (void *p)
{
  struct f2_data *d = (struct f2_data *) p;
  long l, istart, iend;
  if (GOMP_loop_static_start (0, 4, 1, 0, &istart, &iend))
    {
      do
	{
	  for (l = istart; l < iend; l++)
	    f2_nested2 (d->a, (int) l);
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void f2 (void)
{
  int a[4], k;
  struct f2_data d = { a };
  for (k = 0; k < 4; k++)
    a[k] = 0;
  GOMP_parallel (f2_body, &d, 0, 0);
  if (a[0] != 42 || a[1] != 42 || a[2] != 42 || a[3] != 42)
    abort ();
}

static void f3_nested (int *a, int *b, int *c, int x)
{ a[x] = b[x] = c[x] = 42; }

struct f34_data { int *a; int *b; int *c; };
static void f34_inner_body (void *p)
{
  struct f34_data *d = (struct f34_data *) p;
  if (GOMP_single_start ())
    {
      d->b[2] = 44;
      d->c[2] = 44;
    }
  GOMP_barrier ();
}
static void f34_outer_body (void *p)
{
  struct f34_data *d = (struct f34_data *) p;
  if (GOMP_single_start ())
    {
      d->a[1] = 43;
      d->b[1] = 43;
      GOMP_parallel (f34_inner_body, d, 0, 0);
    }
  GOMP_barrier ();
}

static void f3 (void)
{
  int a[4], b[4], c[4], k;
  struct f34_data d = { a, b, c };
  for (k = 0; k < 4; k++)
    a[k] = b[k] = c[k] = 0;
  f3_nested (a, b, c, 0);         /* a[0]=b[0]=c[0]=42 */
  GOMP_parallel (f34_outer_body, &d, 0, 0);
  if (a[0] != 42 || a[1] != 43 || a[2] != 0 || a[3] != 0)
    abort ();
  if (b[0] != 42 || b[1] != 43 || b[2] != 44 || b[3] != 0)
    abort ();
  if (c[0] != 42 || c[1] != 0 || c[2] != 44 || c[3] != 0)
    abort ();
}

static void f4 (void)
{
  int a[4], b[4], c[4], k;
  struct f34_data d = { a, b, c };
  for (k = 0; k < 4; k++)
    a[k] = b[k] = c[k] = (k == 0 ? 42 : 0);
  GOMP_parallel (f34_outer_body, &d, 0, 0);
  if (a[0] != 42 || a[1] != 43 || a[2] != 0 || a[3] != 0)
    abort ();
  if (b[0] != 42 || b[1] != 43 || b[2] != 44 || b[3] != 0)
    abort ();
  if (c[0] != 42 || c[1] != 0 || c[2] != 44 || c[3] != 0)
    abort ();
}

int main (void)
{
  f1 ();
  f2 ();
  f3 ();
  f4 ();
  return 0;
}
