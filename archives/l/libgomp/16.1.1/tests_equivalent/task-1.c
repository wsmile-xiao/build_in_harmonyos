/* Equiv-rewrite of upstream task-1.c.
 * #pragma omp task (private/shared/untied), taskwait, sections, parallel+master
 * manually lowered to GOMP ABI (link against libgomp.so).
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

#define GOMP_TASK_FLAG_UNTIED 1

int a = 18;
int v1 = 1, v2 = 2, v5 = 5;
int e;

struct f1_data { int *k; int *n; int i; int l; };

static void f1_task (void *p)
{
  struct f1_data *d = (struct f1_data *) p;
  int j, m;			/* private */
  j = 6;
  m = 5;
  if (++a != 19 || ++d->i != 9 || j != 6 || ++d->l != 7 || m != 5
      || ++*d->n != 9)
    {
      GOMP_atomic_start ();
      (*d->k)++;
      GOMP_atomic_end ();
    }
}

static void
f1 (int i, int j, int k, int untied)
{
  int l = 6, m = 7, n = 8;
  struct f1_data d;
  d.k = &k;
  d.n = &n;
  d.i = i;
  d.l = l;
  GOMP_task (f1_task, &d, NULL, sizeof d, _Alignof (struct f1_data), 1,
	     untied ? GOMP_TASK_FLAG_UNTIED : 0, NULL, 0, NULL);
  GOMP_taskwait ();
  if (a != 19 || i != 8 || j != 26 || k != 0 || l != 6 || m != 7 || n != 9)
    abort ();
}

struct f2_data { int v1, v2, v3, v4; };

static void
f2_task (void *p)
{
  struct f2_data *d = (struct f2_data *) p;
  if (++d->v1 != 8 || ++d->v2 != 3 || ++d->v3 != 4 || ++d->v4 != 5
      || ++v5 != 6)
    e = 1;
}

static void
f2 (void)
{
  int v3 = 3;
  /* sections private(v1) firstprivate(v2) with a single section,
     executed by the initial (single-threaded) team.  */
  int v1_priv;			/* private v1 (uninitialized) */
  int v2_fp = v2;		/* firstprivate v2 */
  int v4 = 4;			/* section-local */
  struct f2_data d;

  v1_priv = 7;
  d.v1 = v1_priv;		/* task firstprivate */
  d.v2 = v2_fp;
  d.v3 = v3;
  d.v4 = v4;
  GOMP_task (f2_task, &d, NULL, sizeof d, _Alignof (struct f2_data), 1, 0,
	     NULL, 0, NULL);
  GOMP_taskwait ();
  if (v1_priv != 7 || v2_fp != 2 || v3 != 3 || v4 != 4 || v5 != 6)
    abort ();
  if (e)
    abort ();
}

static void
parallel_body (void *p)
{
  /* #pragma omp master */
  if (omp_get_thread_num () == 0)
    {
      f1 (8, 26, 0, 0);
      a = 18;
      f1 (8, 26, 0, 1);		/* untied variant */
    }
}

int
main (void)
{
  f1 (8, 26, 0, 0);
  f2 ();
  a = 18;
  f1 (8, 26, 0, 1);
  a = 18;
  GOMP_parallel (parallel_body, NULL, 4, 0);
  return 0;
}
