/* Equiv-rewrite of upstream pr42942.c.
 * Tests omp_set_max_active_levels and nested parallel serialization with
 * reduction(|:e). Each level computes its private e (0/1) and OR-folds it into
 * the parent's accumulator (which is the parent's private reduction variable).
 */
#include <omp.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);

struct lvl { int *acc; };

static void
fold (int *acc, int e)
{
  if (e)
    { GOMP_atomic_start (); *acc |= e; GOMP_atomic_end (); }
}

/* ---- Case 1: max_active_levels = 1 ---- */
static void L2_c1 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (!omp_in_parallel () || omp_get_num_threads () != 1)
    e = 1;
  fold (d->acc, e);
}
static void L1_c1 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (!omp_in_parallel () || omp_get_num_threads () != 2)
    e = 1;
  else
    {
      struct lvl d2 = { &e };
      GOMP_parallel (L2_c1, &d2, 2, 0);
    }
  fold (d->acc, e);
}

/* ---- Case 2: max_active_levels = 0 ---- */
static void L2_c2 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (omp_in_parallel () || omp_get_num_threads () != 1)
    e = 1;
  fold (d->acc, e);
}
static void L1_c2 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (omp_in_parallel () || omp_get_num_threads () != 1)
    e = 1;
  else
    {
      struct lvl d2 = { &e };
      GOMP_parallel (L2_c2, &d2, 2, 0);
    }
  fold (d->acc, e);
}

/* ---- Case 3: max_active_levels = 2 ---- */
static void L3_c3 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (!omp_in_parallel () || omp_get_num_threads () != 1)
    e = 1;
  fold (d->acc, e);
}
static void L2_c3 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (!omp_in_parallel () || omp_get_num_threads () != 2)
    e = 1;
  else
    {
      struct lvl d2 = { &e };
      GOMP_parallel (L3_c3, &d2, 2, 0);
    }
  fold (d->acc, e);
}
static void L1_c3 (void *p)
{
  struct lvl *d = (struct lvl *) p;
  int e = 0;
  if (!omp_in_parallel () || omp_get_num_threads () != 2)
    e = 1;
  else
    {
      struct lvl d2 = { &e };
      GOMP_parallel (L2_c3, &d2, 2, 0);
    }
  fold (d->acc, e);
}

int
main (void)
{
  int e = 0;
  omp_set_dynamic (0);
  omp_set_nested (1);

  omp_set_max_active_levels (1);
  if (omp_get_max_active_levels () != 1)
    abort ();
  e = 0;
  { struct lvl d1 = { &e }; GOMP_parallel (L1_c1, &d1, 2, 0); }
  if (e)
    abort ();

  omp_set_max_active_levels (0);
  if (omp_get_max_active_levels () != 0)
    abort ();
  e = 0;
  { struct lvl d1 = { &e }; GOMP_parallel (L1_c2, &d1, 2, 0); }
  if (e)
    abort ();

  omp_set_max_active_levels (2);
  if (omp_get_max_active_levels () != 2)
    abort ();
  e = 0;
  { struct lvl d1 = { &e }; GOMP_parallel (L1_c3, &d1, 2, 0); }
  if (e)
    abort ();

  return 0;
}
