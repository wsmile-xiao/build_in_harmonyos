/* Equiv-rewrite of upstream vla-1.c.
 * - main(int argc, char **argv[]) -> main(int argc, char **argv)
 * - #pragma omp parallel default(shared) num_threads(4)
 *     firstprivate(a,m) private(b,i) reduction(+:l)
 *     -> GOMP_parallel + manual firstprivate (copy of VLA a), private b/i,
 *        manual per-thread reduction on l.
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>
#include "libgomp_g.h"

struct data
{
  int n, m;
  char *a0;      /* shared source of firstprivate a (initial values) */
  int *c;        /* shared c */
  int l[4];      /* per-thread reduction(+:l) private copies */
};

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int n = d->n, m = d->m;
  int tid = omp_get_thread_num ();
  char a[n + 3];
  unsigned short b[n / 2 - 1];
  int i;
  int *l = &d->l[tid];

  /* firstprivate(a): each thread gets its own copy of a's initial values. */
  memcpy (a, d->a0, (size_t) (n + 3) * sizeof (char));

  for (i = 0; i < m + 3; i++)
    if (a[i] != i)
      (*l)++;
  for (i = 0; i < m * 2 + 1; i++)
    if (d->c[i] != ((i << 24) | i))
      (*l)++;

  GOMP_barrier ();

  memset (a, tid, (size_t) (m + 3));
  for (i = 0; i < m / 2 - 1; i++)
    b[i] = a[0] + 7;

  /* #pragma omp master */
  if (tid == 0)
    for (i = 0; i < m * 2 + 1; i++)
      d->c[i] = a[0] + 16;

  GOMP_barrier ();

  if (a[0] != tid)
    (*l)++;
  for (i = 1; i < m + 3; i++)
    if (a[i] != a[0])
      (*l)++;
  for (i = 0; i < m / 2 - 1; i++)
    if (b[i] != a[0] + 7)
      (*l)++;
  for (i = 0; i < m * 2 + 1; i++)
    if (d->c[i] != 16)
      (*l)++;
}

int
main (int argc, char **argv)
{
  int n = argc < 5 ? 12 : 31, i, m, l;
  char a[n + 3];
  unsigned short b[n / 2 - 1];
  int c[n * 2 + 1];
  struct data d;

  (void) argv;

  for (i = 0; i < n + 3; i++)
    a[i] = i;
  for (i = 0; i < n / 2 - 1; i++)
    b[i] = (i << 8) | i;
  for (i = 0; i < n * 2 + 1; i++)
    c[i] = (i << 24) | i;
  l = 0;
  m = n;

  d.n = n;
  d.m = m;
  d.a0 = a;
  d.c = c;
  memset (d.l, 0, sizeof d.l);

  GOMP_parallel (body, &d, 4, 0);

  /* reduction(+:l): combine per-thread copies into l. */
  l = 0;
  for (i = 0; i < 4; i++)
    l += d.l[i];

  if (l)
    abort ();
  for (i = 0; i < n * 2 + 1; i++)
    if (c[i] != 16)
      l++;
  return 0;
}
