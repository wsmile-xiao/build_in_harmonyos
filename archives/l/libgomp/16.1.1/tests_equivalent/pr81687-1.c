/* PR c/81687 - equiv rewrite. parallel with address-of-label (&&lab) ->
 * GOMP_parallel; cross-boundary label addresses passed via data/global.
 */
#include <stdio.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

static void *g_lab3;

static void
body1 (void *arg)
{
  void **dd = (void **) arg;
  void *p1;
lab1:
  p1 = &&lab1;
  printf ("lab1=%p\n", p1);
  printf ("lab2=%p\n", dd[0]);
}

static void
body2 (void *arg)
{
  (void) arg;
  void *p2;
lab3:
  g_lab3 = &&lab3;
  (void) p2;
}

int
main (void)
{
  void *lab2_addr;
lab2:
  lab2_addr = &&lab2;
  void *d1[1] = { lab2_addr };
  GOMP_parallel (body1, d1, 0, 0);
  GOMP_parallel (body2, 0, 0, 0);
  printf ("lab3=%p\n", g_lab3);
  return 0;
}
