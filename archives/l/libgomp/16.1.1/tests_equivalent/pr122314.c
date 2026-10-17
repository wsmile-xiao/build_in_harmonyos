/* PR libgomp/122314 - equiv rewrite. parallel(8) { barrier; init; for task } ->
 * GOMP_parallel + GOMP_loop_static + GOMP_task; total == 10.
 */
#include <stdlib.h>
#include <omp.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, bool, unsigned, void **, int, void *);

#define NUM_THREADS 8
unsigned full_data[NUM_THREADS];

static void
task_body (void *arg)
{
  (void) arg;
  full_data[omp_get_thread_num ()] += 1;
}

static void
par_body (void *arg)
{
  (void) arg;
  GOMP_barrier ();
  full_data[omp_get_thread_num ()] = 0;
  long ist, ien;
  if (GOMP_loop_static_start (0, 10, 1, 0, &ist, &ien))
    {
      do
	{
	  long i;
	  for (i = ist; i < ien; i++)
	    GOMP_task (task_body, 0, 0, 0, 0, 1, 0, 0, 0, 0);
	}
      while (GOMP_loop_static_next (&ist, &ien));
    }
  GOMP_loop_end ();
}

static void
test (void)
{
  int i;
  for (i = 0; i < NUM_THREADS; i++)
    full_data[i] = 0;
  GOMP_parallel (par_body, 0, 8, 0);
  unsigned total = 0;
  for (i = 0; i < NUM_THREADS; i++)
    total += full_data[i];
  if (total != 10)
    abort ();
}

int
main (void)
{
  test ();
  test ();
  return 0;
}
