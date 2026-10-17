/* Equiv-rewrite of upstream depend-1.c.
 * #pragma omp parallel/single/task depend/taskgroup manually lowered to GOMP ABI.
 * depend clauses use the legacy GOMP_task depend array format:
 *   depend[0] = count (nonzero), depend[1] = #out, depend[2..] = addresses.
 */
#include <stdlib.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_task (void (*) (void *), void *, void (*) (void *, void *),
		       long, long, _Bool, unsigned, void **, int, void *);
extern void GOMP_taskwait (void);
extern void GOMP_taskgroup_start (void);
extern void GOMP_taskgroup_end (void);
extern _Bool GOMP_single_start (void);
extern void GOMP_barrier (void);

#define GOMP_TASK_FLAG_DEPEND 8

/* --- task bodies --- */
struct intp { int *x; };	/* shared x */
static void t_set2 (void *p) { struct intp *d = p; *d->x = 2; }
static void t_set1 (void *p) { struct intp *d = p; *d->x = 1; }
static void t_chk1 (void *p) { struct intp *d = p; if (*d->x != 1) abort (); }
static void t_chk2 (void *p) { struct intp *d = p; if (*d->x != 2) abort (); }

struct intv { int x; };		/* firstprivate x */
static void t_fp_out (void *p) { struct intv *d = p; d->x = 2; }
static void t_fp_chk1 (void *p) { struct intv *d = p; if (d->x != 1) abort (); }

static void
run_out (int *x)
{
  struct intp d = { x };
  void *dep[3] = { (void *) 1, (void *) 1, (void *) x };
  GOMP_task (t_set2, &d, NULL, sizeof d, _Alignof (struct intp), 1,
	     GOMP_TASK_FLAG_DEPEND, dep, 0, NULL);
}

static void
run_in (int *x)
{
  struct intp d = { x };
  void *dep[3] = { (void *) 1, (void *) 0, (void *) x };
  GOMP_task (t_chk2, &d, NULL, sizeof d, _Alignof (struct intp), 1,
	     GOMP_TASK_FLAG_DEPEND, dep, 0, NULL);
}

static void
run_out_set1 (int *x)
{
  struct intp d = { x };
  void *dep[3] = { (void *) 1, (void *) 1, (void *) x };
  GOMP_task (t_set1, &d, NULL, sizeof d, _Alignof (struct intp), 1,
	     GOMP_TASK_FLAG_DEPEND, dep, 0, NULL);
}

static void
run_in_chk1 (int *x)
{
  struct intp d = { x };
  void *dep[3] = { (void *) 1, (void *) 0, (void *) x };
  GOMP_task (t_chk1, &d, NULL, sizeof d, _Alignof (struct intp), 1,
	     GOMP_TASK_FLAG_DEPEND, dep, 0, NULL);
}

/* --- dep: x declared outside parallel --- */
static void
dep_parallel (void *p)
{
  int **xp = p;
  if (GOMP_single_start ())
    {
      run_out (*xp);
      run_in (*xp);
    }
  GOMP_barrier ();
}
void
dep (void)
{
  int x = 1;
  int *xp = &x;
  GOMP_parallel (dep_parallel, &xp, 0, 0);
}

/* --- dep2: x declared inside single --- */
static void
dep2_parallel (void *p)
{
  if (GOMP_single_start ())
    {
      int x = 1;
      run_out (&x);
      run_in (&x);
      GOMP_taskwait ();
    }
  GOMP_barrier ();
}
void
dep2 (void)
{
  GOMP_parallel (dep2_parallel, NULL, 0, 0);
}

/* --- dep3: x declared inside parallel --- */
static void
dep3_parallel (void *p)
{
  int x = 1;
  if (GOMP_single_start ())
    {
      run_out (&x);
      run_in (&x);
    }
  GOMP_barrier ();
}
void
dep3 (void)
{
  GOMP_parallel (dep3_parallel, NULL, 0, 0);
}

/* --- firstpriv: x default firstprivate in tasks --- */
static void
firstpriv_parallel (void *p)
{
  if (GOMP_single_start ())
    {
      int x = 1;
      struct intv d1 = { x };
      void *dep_out[3] = { (void *) 1, (void *) 1, (void *) &x };
      GOMP_task (t_fp_out, &d1, NULL, sizeof d1, _Alignof (struct intv), 1,
		 GOMP_TASK_FLAG_DEPEND, dep_out, 0, NULL);
      struct intv d2 = { x };
      void *dep_in[3] = { (void *) 1, (void *) 0, (void *) &x };
      GOMP_task (t_fp_chk1, &d2, NULL, sizeof d2, _Alignof (struct intv), 1,
		 GOMP_TASK_FLAG_DEPEND, dep_in, 0, NULL);
    }
  GOMP_barrier ();
}
void
firstpriv (void)
{
  GOMP_parallel (firstpriv_parallel, NULL, 0, 0);
}

/* --- antidep: in-then-out anti-dependency --- */
static void
antidep_parallel (void *p)
{
  int **xp = p;
  if (GOMP_single_start ())
    {
      run_in_chk1 (*xp);
      run_out (*xp);
    }
  GOMP_barrier ();
}
void
antidep (void)
{
  int x = 1;
  int *xp = &x;
  GOMP_parallel (antidep_parallel, &xp, 0, 0);
}

/* --- antidep2: taskgroup --- */
static void
antidep2_parallel (void *p)
{
  if (GOMP_single_start ())
    {
      int x = 1;
      GOMP_taskgroup_start ();
      run_in_chk1 (&x);
      run_out (&x);
      GOMP_taskgroup_end ();
    }
  GOMP_barrier ();
}
void
antidep2 (void)
{
  GOMP_parallel (antidep2_parallel, NULL, 0, 0);
}

/* --- antidep3 --- */
static void
antidep3_parallel (void *p)
{
  int x = 1;
  if (GOMP_single_start ())
    {
      run_in_chk1 (&x);
      run_out (&x);
    }
  GOMP_barrier ();
}
void
antidep3 (void)
{
  GOMP_parallel (antidep3_parallel, NULL, 0, 0);
}

/* --- outdep: two out tasks --- */
static void
outdep_parallel (void *p)
{
  if (GOMP_single_start ())
    {
      int x = 0;
      run_out_set1 (&x);
      run_out (&x);
      GOMP_taskwait ();
      if (x != 2)
	abort ();
    }
  GOMP_barrier ();
}
void
outdep (void)
{
  GOMP_parallel (outdep_parallel, NULL, 0, 0);
}

/* --- concurrent: 1 out + 3 in, x outside parallel --- */
static void
concurrent_parallel (void *p)
{
  int **xp = p;
  if (GOMP_single_start ())
    {
      run_out (*xp);
      run_in (*xp);
      run_in (*xp);
      run_in (*xp);
    }
  GOMP_barrier ();
}
void
concurrent (void)
{
  int x = 1;
  int *xp = &x;
  GOMP_parallel (concurrent_parallel, &xp, 0, 0);
}

/* --- concurrent2: x inside single, with taskwait --- */
static void
concurrent2_parallel (void *p)
{
  if (GOMP_single_start ())
    {
      int x = 1;
      run_out (&x);
      run_in (&x);
      run_in (&x);
      run_in (&x);
      GOMP_taskwait ();
    }
  GOMP_barrier ();
}
void
concurrent2 (void)
{
  GOMP_parallel (concurrent2_parallel, NULL, 0, 0);
}

/* --- concurrent3: x inside parallel --- */
static void
concurrent3_parallel (void *p)
{
  int x = 1;
  if (GOMP_single_start ())
    {
      run_out (&x);
      run_in (&x);
      run_in (&x);
      run_in (&x);
    }
  GOMP_barrier ();
}
void
concurrent3 (void)
{
  GOMP_parallel (concurrent3_parallel, NULL, 0, 0);
}

int
main (void)
{
  dep ();
  dep2 ();
  dep3 ();
  firstpriv ();
  antidep ();
  antidep2 ();
  antidep3 ();
  outdep ();
  concurrent ();
  concurrent2 ();
  concurrent3 ();
  return 0;
}
