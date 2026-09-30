/* Equiv-rewrite of upstream libgomp.c/cancel-for-2.c.
 * #pragma omp parallel num_threads(32) shared(v,w) { #pragma omp for { #pragma omp cancel for if(...) } ... }
 * manually lowered to GOMP ABI.  Run with OMP_CANCELLATION=true. */
#include <stdlib.h>
#include <omp.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern _Bool GOMP_cancel (int, _Bool);

#define GOMP_CANCEL_PARALLEL 1
#define GOMP_CANCEL_LOOP 2

struct data { int *x; int *v; int *w; };

/* A static-scheduled #pragma omp for over [0,n).  For each iteration, first
 * perform "cancel for if(do_cancel)"; if the cancellation fires, leave the
 * loop immediately, otherwise run action (a single statement/block). */
#define CANCEL_FOR(n, do_cancel, action) do {			\
    long _istart, _iend, _i;					\
    if (GOMP_loop_static_start (0, (n), 1, 1, &_istart, &_iend))	\
      {								\
	int _cancelled = 0;					\
	do							\
	  {							\
	    for (_i = _istart; _i < _iend; _i++)		\
	      {							\
		if (GOMP_cancel (GOMP_CANCEL_LOOP, (do_cancel))) \
		  { _cancelled = 1; break; }			\
		action;						\
	      }							\
	    if (_cancelled)					\
	      break;						\
	  }							\
	while (GOMP_loop_static_next (&_istart, &_iend));	\
      }								\
    GOMP_loop_end ();						\
  } while (0)

static void
region1 (void *p)
{
  struct data *d = p;
  int *x = d->x, *v = d->v, *w = d->w;

  CANCEL_FOR (1000, x[0], abort ());
  CANCEL_FOR (1000, x[1], { GOMP_atomic_start (); (*v)++; GOMP_atomic_end (); });
  CANCEL_FOR (1000, x[2], { GOMP_atomic_start (); (*w) += 8; GOMP_atomic_end (); });
  CANCEL_FOR (1000, x[3], { GOMP_atomic_start (); (*v) += 2; GOMP_atomic_end (); });
}

static void
region2 (void *p)
{
  struct data *d = p;
  int *x = d->x, *v = d->v, *w = d->w;

  /* None of these "cancel parallel" directives actually cancel (x[4] == 0),
     but the workshares are still cancellable. */
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, omp_get_thread_num () == 1 && x[4]))
    return;
  CANCEL_FOR (1000, x[0], abort ());
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, omp_get_thread_num () == 2 && x[4]))
    return;
  CANCEL_FOR (1000, x[1], { GOMP_atomic_start (); (*v)++; GOMP_atomic_end (); });
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, omp_get_thread_num () == 3 && x[4]))
    return;
  CANCEL_FOR (1000, x[2], { GOMP_atomic_start (); (*w) += 8; GOMP_atomic_end (); });
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, omp_get_thread_num () == 4 && x[4]))
    return;
  CANCEL_FOR (1000, x[3], { GOMP_atomic_start (); (*v) += 2; GOMP_atomic_end (); });
  if (GOMP_cancel (GOMP_CANCEL_PARALLEL, omp_get_thread_num () == 5 && x[4]))
    return;
}

__attribute__((noinline, noclone)) static void
foo (int *x)
{
  int v = 0, w = 0;
  struct data d = { x, &v, &w };

  GOMP_parallel (region1, &d, 32, 0);
  if (v != 3000 || w != 0)
    abort ();

  GOMP_parallel (region2, &d, 32, 0);
  if (v != 6000 || w != 0)
    abort ();
}

int
main (void)
{
  int x[] = { 1, 0, 1, 0, 0 };
  if (omp_get_cancellation ())
    foo (x);
  return 0;
}
