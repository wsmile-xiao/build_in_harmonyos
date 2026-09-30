/* Equivalent rewrite: task firstprivate(VLA p,q) -> GOMP_task with packed data copy */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>
#include <string.h>

int e;

static void
baz (int i, int *p, int j, int *q)
{
  if (p[0] != 1 || p[i] != 3 || q[0] != 2 || q[j] != 4)
    {
      GOMP_atomic_start ();
      e++;
      GOMP_atomic_end ();
    }
}

static void
task4_fn (void *vp)
{
  unsigned char *buf = (unsigned char *) vp;
  int i, j;
  int *p, *q;

  memcpy (&i, buf, sizeof (int));
  memcpy (&j, buf + sizeof (int), sizeof (int));
  p = (int *) (buf + 2 * sizeof (int));
  q = (int *) (buf + 2 * sizeof (int) + (i + 1) * sizeof (int));

  baz (i, p, j, q);
}

static void
foo (int i, int j)
{
  int p[i + 1];
  int q[j + 1];
  size_t size;
  unsigned char *buf;

  memset (p, 0, sizeof (p));
  memset (q, 0, sizeof (q));
  p[0] = 1;
  p[i] = 3;
  q[0] = 2;
  q[j] = 4;

  size = 2 * sizeof (int) + (i + 1) * sizeof (int) + (j + 1) * sizeof (int);
  buf = (unsigned char *) malloc (size);
  memcpy (buf, &i, sizeof (int));
  memcpy (buf + sizeof (int), &j, sizeof (int));
  memcpy (buf + 2 * sizeof (int), p, (i + 1) * sizeof (int));
  memcpy (buf + 2 * sizeof (int) + (i + 1) * sizeof (int), q,
	  (j + 1) * sizeof (int));

  GOMP_task (task4_fn, buf, NULL, size, sizeof (int), 1, 0, NULL, 0, NULL);

  free (buf);
}

static void
main_fn (void *vp)
{
  (void) vp;
  foo (5 + omp_get_thread_num (), 7 + omp_get_thread_num ());
}

int
main (void)
{
  GOMP_parallel (main_fn, NULL, 4, 0);

  if (e)
    abort ();

  return 0;
}
