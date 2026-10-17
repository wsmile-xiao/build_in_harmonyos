/* Equiv-rewrite of upstream nested-3.c.
 * #pragma omp parallel [if(0)] [num_threads] [firstprivate] -> GOMP_parallel.
 * parallel if(0) -> GOMP_parallel(fn,data,1,0) (serialized but still a new task).
 * #pragma omp atomic -> GOMP_atomic_start/end.
 * Level/active-level/ancestor/team-size semantics are maintained by libgomp.
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

struct l3_data { int *e; int tn1; int tn2; };
static void l3_body (void *p)
{
  struct l3_data *d = (struct l3_data *) p;
  int tn3 = omp_get_thread_num ();
  if (omp_in_parallel () != 1
      || omp_get_num_threads () != 2
      || tn3 > 1 || tn3 < 0
      || omp_get_level () != 3
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != d->tn1
      || omp_get_ancestor_thread_num (2) != d->tn2
      || omp_get_ancestor_thread_num (3) != tn3
      || omp_get_ancestor_thread_num (-1) != -1
      || omp_get_ancestor_thread_num (4) != -1
      || omp_get_team_size (0) != 1
      || omp_get_team_size (1) != 4
      || omp_get_team_size (2) != 1
      || omp_get_team_size (3) != 2
      || omp_get_team_size (-1) != -1
      || omp_get_team_size (4) != -1
      || omp_get_active_level () != 2)
    {
      GOMP_atomic_start ();
      d->e[2]++;
      GOMP_atomic_end ();
    }
}

struct l2_data { int *e; int tn1; };
static void l2_body (void *p)
{
  struct l2_data *d = (struct l2_data *) p;
  int tn2 = omp_get_thread_num ();
  if (omp_in_parallel () != 1
      || omp_get_num_threads () != 1
      || tn2 != 0
      || omp_get_level () != 2
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != d->tn1
      || omp_get_ancestor_thread_num (2) != tn2
      || omp_get_ancestor_thread_num (-1) != -1
      || omp_get_ancestor_thread_num (3) != -1
      || omp_get_team_size (0) != 1
      || omp_get_team_size (1) != 4
      || omp_get_team_size (2) != 1
      || omp_get_team_size (-1) != -1
      || omp_get_team_size (3) != -1
      || omp_get_active_level () != 1)
    {
      GOMP_atomic_start ();
      d->e[1]++;
      GOMP_atomic_end ();
    }

  {
    struct l3_data d3 = { d->e, d->tn1, tn2 };
    GOMP_parallel (l3_body, &d3, 2, 0);
  }
}

struct l1_data { int *e; };
static void l1_body (void *p)
{
  struct l1_data *d = (struct l1_data *) p;
  int tn1 = omp_get_thread_num ();
  if (omp_in_parallel () != 1
      || omp_get_num_threads () != 4
      || tn1 >= 4 || tn1 < 0
      || omp_get_level () != 1
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (1) != tn1
      || omp_get_ancestor_thread_num (-1) != -1
      || omp_get_ancestor_thread_num (2) != -1
      || omp_get_team_size (0) != 1
      || omp_get_team_size (1) != omp_get_num_threads ()
      || omp_get_team_size (-1) != -1
      || omp_get_team_size (2) != -1
      || omp_get_active_level () != 1)
    {
      GOMP_atomic_start ();
      d->e[0]++;
      GOMP_atomic_end ();
    }

  {
    struct l2_data d2 = { d->e, tn1 };
    GOMP_parallel (l2_body, &d2, 1, 0);   /* parallel if(0) -> 1 thread */
  }
}

int main (void)
{
  int e[3];
  struct l1_data d = { e };

  memset (e, '\0', sizeof (e));
  omp_set_nested (1);
  omp_set_dynamic (0);

  if (omp_in_parallel ()
      || omp_get_level () != 0
      || omp_get_ancestor_thread_num (0) != 0
      || omp_get_ancestor_thread_num (-1) != -1
      || omp_get_ancestor_thread_num (1) != -1
      || omp_get_team_size (0) != 1
      || omp_get_team_size (-1) != -1
      || omp_get_team_size (1) != -1
      || omp_get_active_level () != 0)
    abort ();

  GOMP_parallel (l1_body, &d, 4, 0);

  if (e[0] || e[1] || e[2])
    abort ();
  return 0;
}
