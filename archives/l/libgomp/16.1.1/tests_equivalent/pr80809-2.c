/* Equiv-rewrite of upstream pr80809-2.c.
 * parallel + single, then 16 tasks each with firstprivate(v) and shared w.
 * v is a VLA; the firstprivate copy is made per task.
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_single_start (void);
extern void GOMP_barrier (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);

struct task_d { int x; int *v; int *w; int i; };

static void
task_body (void *p)
{
  struct task_d *d = (struct task_d *) p;
  for (int j = 0; j < d->x; j++)
    d->v[j] += d->i;
  for (int j = 0; j < d->x; j++)
    d->w[d->i] += d->v[j];
}

struct par_d { int x; int *v; int *w; };

static void
single_body (void *p)
{
  struct par_d *d = (struct par_d *) p;
  struct task_d tds[16];
  for (int i = 0; i < 16; i++)
    {
      tds[i].x = d->x;
      tds[i].v = malloc ((size_t) d->x * sizeof (int));
      memcpy (tds[i].v, d->v, (size_t) d->x * sizeof (int));
      tds[i].w = d->w;
      tds[i].i = i;
      GOMP_task (task_body, &tds[i], NULL,
		 sizeof (struct task_d), __alignof__ (struct task_d),
		 1, 0, NULL, 0, NULL);
    }
  GOMP_taskwait ();
  for (int i = 0; i < 16; i++)
    free (tds[i].v);
}

static void
par_body (void *p)
{
  if (GOMP_single_start ())
    single_body (p);
  GOMP_barrier ();
}

__attribute__((noinline)) void
foo (int x)
{
  int v[x], w[16];
  for (int i = 0; i < x; i++)
    v[i] = i;
  for (int i = 0; i < 16; i++)
    w[i] = 0;
  struct par_d pd = { x, v, w };
  GOMP_parallel (par_body, &pd, 0, 0);
  for (int i = 0; i < 16; i++)
    if (w[i] != (x - 1) * x / 2 + x * i)
      __builtin_abort ();
}

int
main (void)
{
  foo (4);
  foo (27);
  foo (196);
  return 0;
}
