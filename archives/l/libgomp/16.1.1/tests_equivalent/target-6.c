#include <omp.h>
#include <stdlib.h>
#include <stdbool.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);
void GOMP_teams_reg (void (*)(void *), void *, unsigned, unsigned, unsigned);

static void
par2_body (void *d)
{
  (void) d;
  if (!omp_in_parallel ()
      || omp_get_level () != 1
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != omp_get_thread_num ()
      || omp_get_ancestor_thread_num (2) != -1)
    abort ();
}

static void
tgtA_body (void *d)
{
  (void) d;
  if (omp_in_parallel ()
      || omp_get_level () != 0
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != -1)
    abort ();
  GOMP_parallel (par2_body, NULL, 2, 0);
}

static void
teamsB_body (void *d)
{
  (void) d;
  for (int i = 0; i < 1; ++i)
    if (omp_in_parallel ()
	|| omp_get_level () != 0
	|| omp_get_ancestor_thread_num (0) != 0
	|| omp_get_ancestor_thread_num (1) != -1)
      abort ();
  GOMP_parallel (par2_body, NULL, 2, 0);
}

static void
tgtB_body (void *d)
{
  (void) d;
  GOMP_teams_reg (teamsB_body, NULL, 0, 2, 0);
}

static void
inner_body (void *d)
{
  (void) d;
  if (omp_get_thread_num () == 1)
    {
      if (!omp_in_parallel ()
	  || omp_get_level () != 2
	  || omp_get_ancestor_thread_num (0) != 0
	  || omp_get_ancestor_thread_num (1) != 2
	  || omp_get_ancestor_thread_num (2) != 1
	  || omp_get_ancestor_thread_num (3) != -1)
	abort ();
      GOMP_target (omp_get_initial_device (), tgtA_body, NULL, 0, NULL, NULL, NULL);
      GOMP_target (omp_get_initial_device (), tgtB_body, NULL, 0, NULL, NULL, NULL);
    }
}

static void
outer_body (void *d)
{
  (void) d;
  if (omp_get_thread_num () == 2)
    {
      if (!omp_in_parallel ())
	abort ();
      GOMP_parallel (inner_body, NULL, 3, 0);
    }
}

int
main ()
{
  omp_set_dynamic (0);
  omp_set_nested (1);
  if (omp_in_parallel ())
    abort ();
  GOMP_parallel (outer_body, NULL, 3, 0);
  return 0;
}
