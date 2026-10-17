/* Equiv-rewrite of upstream task-2.c.
 * GNU nested fn nested(x) reading a -> static fn (pass a by value).
 * #pragma omp task -> GOMP_task; #pragma omp taskwait -> GOMP_taskwait.
 * Task default data-sharing is firstprivate: a and e are private copies inside
 * the task, so the atomic e+=1 (never fires) touches only the private copy.
 * #pragma omp parallel reduction(+:e) -> GOMP_parallel + manual + reduction.
 */
#include <omp.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);

#define MAXT 128

static int nested (int x, int a) { return x + a; }

/* f1: task body has firstprivate a (=6), firstprivate e (=0) */
struct f1_data { int a; };
static void f1_body (void *p)
{
  struct f1_data *d = (struct f1_data *) p;
  int e = 0;                    /* firstprivate copy of e */
  int n = nested (5, d->a);     /* firstprivate a */
  if (n != 11)
    e += 1;                     /* atomic on private copy == plain */
}

static int f1 (void)
{
  int a = 6, e = 0;
  struct f1_data d = { a };
  GOMP_task (f1_body, &d, 0, sizeof (struct f1_data),
	     _Alignof (struct f1_data), 1, 0, 0, 0, 0);
  GOMP_taskwait ();
  return e;
}

/* f2: a = nested(4) = 10, then task checks firstprivate a == 10 */
static void f2_body (void *p)
{
  struct f1_data *d = (struct f1_data *) p;
  int e = 0;
  if (d->a != 10)
    e += 1;
}

static int f2 (void)
{
  int a = 6, e = 0;
  a = nested (4, a);
  {
    struct f1_data d = { a };
    GOMP_task (f2_body, &d, 0, sizeof (struct f1_data),
	       _Alignof (struct f1_data), 1, 0, 0, 0, 0);
    GOMP_taskwait ();
  }
  return e;
}

static int e_priv[MAXT];

static void main_body (void *p)
{
  int tn = omp_get_thread_num ();
  int e = 0;                     /* reduction(+) private, neutral 0 */
  e += f1 ();
  e += f2 ();
  e_priv[tn] = e;
}

int main (void)
{
  int e = 0;
  int t;
  memset (e_priv, 0, sizeof e_priv);
  GOMP_parallel (main_body, 0, 4, 0);
  for (t = 0; t < MAXT; t++)
    e += e_priv[t];
  if (e)
    abort ();
  return 0;
}
