/* Equiv-rewrite of upstream pr26943-1.c.
 * #pragma omp parallel for num_threads(16) firstprivate(n) lastprivate(n)
 * schedule(static,1) reduction(+:x) over i in [0,16).
 */
#include <omp.h>
#include <stdlib.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

int n = 6;

struct d { int *x_partials; long last_n; };

static void
body (void *p)
{
  struct d *d = (struct d *) p;
  int tid = omp_get_thread_num ();
  int nn = 6;            /* firstprivate(n): copy of the global n == 6 */
  int local_x = 0;       /* reduction(+:x) private accumulator */
  long istart, iend;
  if (GOMP_loop_static_start (0, 16, 1, 1, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  {
	    if (nn != 6)
	      ++local_x;
	    nn = i;
	    if (i == 15)
	      d->last_n = nn;   /* lastprivate(n): value from last iteration */
	  }
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->x_partials[tid] = local_x;
}

int
main (void)
{
  int x = 0;
  omp_set_dynamic (0);
  int nt = omp_get_max_threads ();
  if (nt < 16) nt = 16;
  int *partials = calloc ((size_t) nt, sizeof (int));
  struct d d = { partials, 6 };
  GOMP_parallel (body, &d, 16, 0);
  for (int t = 0; t < nt; t++)
    x += partials[t];
  n = (int) d.last_n;   /* lastprivate(n) write-back */
  free (partials);
  if (x || n != 15)
    abort ();
  return 0;
}
