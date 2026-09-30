/* PR other/39591 (task in noinline fn, shared private array) - equiv rewrite.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>
#include <stddef.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_dynamic_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_dynamic_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

static int e;

struct tctx { int *array; int *e; };

static void
task_body (void *arg)
{
  struct tctx *x = (struct tctx *) arg;
  int j;
  for (j = 0; j < 40; j++)
    if (x->array[j] != 0x55555555)
      { GOMP_atomic_start (); (*x->e)++; GOMP_atomic_end (); }
}

static void
foo (int *array)
{
  struct tctx tc = { array, &e };
  GOMP_task (task_body, &tc, 0, sizeof (tc), _Alignof (struct tctx),
	     1, 0, 0, 0, 0);
}

static void
par_body (void *arg)
{
  (void) arg;
  int array[40];
  int i;
  for (i = 0; i < 40; i++)
    array[i] = 0x55555555;
  long ist, ien;
  if (GOMP_loop_dynamic_start (0, 50, 1, 1, &ist, &ien))
    {
      do
	{
	  long k;
	  for (k = ist; k < ien; k++)
	    foo (array);
	}
      while (GOMP_loop_dynamic_next (&ist, &ien));
    }
  GOMP_loop_end ();
  GOMP_taskwait ();
}

int
main (void)
{
  e = 0;
  GOMP_parallel (par_body, 0, 0, 0);
  if (e)
    abort ();
  return 0;
}
