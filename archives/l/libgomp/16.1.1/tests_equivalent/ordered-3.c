/* Equiv-rewrite of upstream libgomp.c/ordered-3.c.
 * "parallel for ordered schedule(...) num_threads(4) if(...)" lowered to GOMP ABI:
 * GOMP_loop_ordered_*_start + GOMP_ordered_start/end. */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_ordered_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_ordered_static_next (long *, long *);
extern _Bool GOMP_loop_ordered_dynamic_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_ordered_dynamic_next (long *, long *);
extern _Bool GOMP_loop_ordered_guided_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_ordered_guided_next (long *, long *);
extern _Bool GOMP_loop_ordered_runtime_start (long, long, long, long *, long *);
extern _Bool GOMP_loop_ordered_runtime_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_ordered_start (void);
extern void GOMP_ordered_end (void);

static int cnt;

static void
check (int x)
{
  if (cnt++ != x)
    abort ();
}

static void
b_static (void *d)
{
  (void) d;
  long j, is, ie;
  if (GOMP_loop_ordered_static_start (0, 1000, 1, 1, &is, &ie))
    {
      do
	{
	  for (j = is; j < ie; j++)
	    {
	      GOMP_ordered_start ();
	      check (j);
	      GOMP_ordered_end ();
	    }
	}
      while (GOMP_loop_ordered_static_next (&is, &ie));
    }
  GOMP_loop_end ();
}

static void
b_dynamic (void *d)
{
  (void) d;
  long j, is, ie;
  if (GOMP_loop_ordered_dynamic_start (0, 1000, 1, 1, &is, &ie))
    {
      do
	{
	  for (j = is; j < ie; j++)
	    {
	      GOMP_ordered_start ();
	      check (j);
	      GOMP_ordered_end ();
	    }
	}
      while (GOMP_loop_ordered_dynamic_next (&is, &ie));
    }
  GOMP_loop_end ();
}

static void
b_guided (void *d)
{
  (void) d;
  long j, is, ie;
  if (GOMP_loop_ordered_guided_start (0, 1000, 1, 1, &is, &ie))
    {
      do
	{
	  for (j = is; j < ie; j++)
	    {
	      GOMP_ordered_start ();
	      check (j);
	      GOMP_ordered_end ();
	    }
	}
      while (GOMP_loop_ordered_guided_next (&is, &ie));
    }
  GOMP_loop_end ();
}

static void
b_runtime (void *d)
{
  (void) d;
  long j, is, ie;
  if (GOMP_loop_ordered_runtime_start (0, 1000, 1, &is, &ie))
    {
      do
	{
	  for (j = is; j < ie; j++)
	    {
	      GOMP_ordered_start ();
	      check (j);
	      GOMP_ordered_end ();
	    }
	}
      while (GOMP_loop_ordered_runtime_next (&is, &ie));
    }
  GOMP_loop_end ();
}

int
main (void)
{
  cnt = 0;
  GOMP_parallel (b_static, 0, 1, 0);	/* if(0) -> serialized */
  cnt = 0;
  GOMP_parallel (b_static, 0, 4, 0);

  cnt = 0;
  GOMP_parallel (b_runtime, 0, 1, 0);
  cnt = 0;
  GOMP_parallel (b_runtime, 0, 4, 0);

  cnt = 0;
  GOMP_parallel (b_dynamic, 0, 1, 0);
  cnt = 0;
  GOMP_parallel (b_dynamic, 0, 4, 0);

  cnt = 0;
  GOMP_parallel (b_guided, 0, 1, 0);
  cnt = 0;
  GOMP_parallel (b_guided, 0, 4, 0);

  return 0;
}
