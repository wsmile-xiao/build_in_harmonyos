/* Equiv-rewrite of upstream private-1.c.
 * #pragma omp parallel private/shared/firstprivate -> GOMP_parallel with a data
 *   struct holding shared pointers and firstprivate values; private vars become
 *   locals in the outlined body.
 * #pragma omp sections/section -> GOMP_sections_start/end (1-based).
 * #pragma omp atomic -> GOMP_atomic_start/end.
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern unsigned GOMP_sections_start (unsigned);
extern void GOMP_sections_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

int a = 18;

struct f1_data { int *k; int *n; int i; int l; };
static void f1_body (void *p)
{
  struct f1_data *d = (struct f1_data *) p;
  int j;                 /* private (uninitialized) */
  int m;                 /* private (uninitialized) */
  int i = d->i;          /* firstprivate */
  int l = d->l;          /* firstprivate */
  j = 6;
  m = 5;
  if (++a != 19 || ++i != 9 || j != 6 || ++l != 7 || m != 5 || ++(*d->n) != 9)
    {
      GOMP_atomic_start ();
      (*d->k)++;
      GOMP_atomic_end ();
    }
}

static void f1 (int i, int j, int k)
{
  int l = 6, m = 7, n = 8;
  struct f1_data d = { &k, &n, i, l };
  GOMP_parallel (f1_body, &d, 1, 0);
  if (a != 19 || i != 8 || j != 26 || k != 0 || l != 6 || m != 7 || n != 9)
    abort ();
}

int v1 = 1, v2 = 2, v5 = 5;
int e;

struct f2_inner { int v1, v2, v3, v4; int *v5; };
static void f2_inner_body (void *p)
{
  struct f2_inner *d = (struct f2_inner *) p;
  int v1 = d->v1, v2 = d->v2, v3 = d->v3, v4 = d->v4;
  if (++v1 != 8 || ++v2 != 3 || ++v3 != 4 || ++v4 != 5 || ++(*d->v5) != 6)
    e = 1;
}

static void f2 (void)
{
  int v3 = 3;
  unsigned sec = GOMP_sections_start (1);
  if (sec == 1)
    {
      int v4 = 4;
      int v1_priv;          /* private v1 */
      int v2_fp = v2;       /* firstprivate v2 */
      v1_priv = 7;
      {
	struct f2_inner d = { v1_priv, v2_fp, v3, v4, &v5 };
	GOMP_parallel (f2_inner_body, &d, 1, 0);
      }
      if (v1_priv != 7 || v2_fp != 2 || v3 != 3 || v4 != 4 || v5 != 6)
	abort ();
      if (e)
	abort ();
    }
  GOMP_sections_end ();
}

int main (void)
{
  f1 (8, 26, 0);
  f2 ();
  return 0;
}
