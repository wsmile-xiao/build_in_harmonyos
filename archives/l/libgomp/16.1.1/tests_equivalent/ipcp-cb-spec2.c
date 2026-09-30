/* ipcp-cb-spec2.c — 完全等价改写
 * #pragma omp task test(a) → GOMP_task；补齐 taskwait 保证任务完成。
 */
#include <string.h>

extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);

void
test (int *a)
{
  for (int i = 0; i < 100; i++)
    a[i] = i;
}

struct t
{
  int *a;
};

static void
task_fn (void *arg)
{
  struct t *t = (struct t *) arg;
  test (t->a);
}

int
main (void)
{
  int a[100];
  struct t t;
  __builtin_memset (a, 0, sizeof (a));
  t.a = a;
  GOMP_task (task_fn, &t, NULL, sizeof (t), __alignof__ (struct t),
	     1, 0, NULL, 0, NULL);
  GOMP_taskwait ();
  return 0;
}
