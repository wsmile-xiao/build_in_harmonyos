/* PR middle-end/68960 - equiv rewrite. aligned(256) private/firstprivate array
 * -> GOMP_parallel (private local) + GOMP_task (firstprivate with arg_align=256).
 */
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>
#include <stddef.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_single_start (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

struct aligned_temp { int temp[257]; } __attribute__ ((aligned (256)));

static void
priv_body (void *arg)
{
  (void) arg;
  int temp[257] __attribute__ ((aligned (256)));
  int *p = &temp[0];
  asm volatile ("" : "+g" (p));
  if (((uintptr_t) p) & 255)
    abort ();
}

static void
task_body (void *arg)
{
  struct aligned_temp *t = (struct aligned_temp *) arg;
  int *p = &t->temp[0];
  asm volatile ("" : "+g" (p));
  if (((uintptr_t) p) & 255)
    abort ();
}

static void
single_body (void *arg)
{
  (void) arg;
  struct aligned_temp t = { { 0 } };
  GOMP_task (task_body, &t, 0, sizeof (t), _Alignof (struct aligned_temp),
	     1, 0, 0, 0, 0);
}

static void
single_wrapper (void *arg)
{
  if (GOMP_single_start ())
    single_body (arg);
}

int
main (void)
{
  GOMP_parallel (priv_body, 0, 2, 0);
  GOMP_parallel (single_wrapper, 0, 2, 0);
  return 0;
}
