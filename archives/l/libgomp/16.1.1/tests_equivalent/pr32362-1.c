/* PR middle-end/32362 (static a,b variant) - equiv rewrite.
 * Nested parallel private(b) / firstprivate(a) -> GOMP_parallel (nested).
 */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static int a = 2, b = 4;

struct inner_ctx { int *n; int b; };
struct outer_ctx { int *n; };

static void
inner_body (void *arg)
{
  struct inner_ctx *x = (struct inner_ctx *) arg;
  int a_priv = 2;              /* firstprivate(a): a == 2 */
  int t = omp_get_thread_num ();
  a_priv = (t + a_priv) + 1;
  if (x->b == t)
    x->n[t] = a_priv + (x->b << 4);
}

static void
outer_body (void *arg)
{
  struct outer_ctx *x = (struct outer_ctx *) arg;
  int b_priv = omp_get_thread_num ();   /* private(b) */
  struct inner_ctx ix = { x->n, b_priv };
  GOMP_parallel (inner_body, &ix, 4, 0);
}

int
main (void)
{
  int n[4] = { -1, -1, -1, -1 };
  struct outer_ctx x = { n };
  omp_set_num_threads (4);
  omp_set_dynamic (0);
  omp_set_nested (1);
  GOMP_parallel (outer_body, &x, 4, 0);
  if (n[0] != 3)
    abort ();
  if (n[3] != -1
      && (n[1] != 0x14 || n[2] != 0x25 || n[3] != 0x36))
    abort ();
  return 0;
}
