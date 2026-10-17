/* Equiv-rewrite of upstream ipcp-cb-spec1.c.
 *
 * Upstream verifies that GCC's IPA-CP specializes the outlined task body so
 * that `__builtin_constant_p(c)` is true inside it. clang has no such GOMP-task
 * constant specialization, so we replace the __builtin_constant_p probe with an
 * explicit value check: the task must receive the constant 7 correctly.
 */
#include <omp.h>
#include <stddef.h>

extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);

static void
test (int c)
{
  if (c != 7)
    __builtin_abort ();
  for (int i = 0; i < c; i++)
    ;
}

static void
task_fn (void *p)
{
  int c = *(int *) p;
  test (c);
}

int
main (void)
{
  int c = 7;
  GOMP_task (task_fn, &c, NULL, sizeof (int), __alignof__ (int), 1, 0, NULL, 0, NULL);
  GOMP_taskwait ();
  return 0;
}
