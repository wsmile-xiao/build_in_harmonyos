#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdint.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_single_start (void);
void GOMP_task (void (*)(void *), void *, void (*)(void *, void *), long, long, bool, unsigned, void **, int, void *);
void GOMP_taskwait (void);
void GOMP_barrier (void);

#define DEP_FLAG 8   /* GOMP_TASK_FLAG_DEPEND */

static int x, y, z, s = 11, t = 12, u = 13, w = 7, err;

static void tk_x1 (void *d) { (void)d; usleep (5000); x = 1; }
static void tk_y2 (void *d) { (void)d; usleep (6000); y = 2; }
static void tk_z3 (void *d) { (void)d; usleep (7000); z = 3; }
static void tk_x4 (void *d) { (void)d; usleep (5000); x = 4; }
static void tk_y5 (void *d) { (void)d; usleep (4000); y = 5; }
static void tk_z6 (void *d) { (void)d; usleep (3000); z = 6; }
static void tk_s14 (void *d) { (void)d; usleep (2000); s = 14; }
static void tk_t15 (void *d) { (void)d; usleep (3000); t = 15; }
static void tk_u16 (void *d) { (void)d; usleep (4000); u = 16; }

static void tgt_check1 (void *d) { (void)d; err = (x != 1 || y != 2 || z != 3); }
static void tgt_check2 (void *d) { (void)d; err = (x != 4 || y != 5 || z != 6); x = 7; y = 8; z = 9; }
static void tgt_checkw (void *d) { (void)d; err = (w != 7); w = 17; }

static void
single25 (void *d)
{
  (void) d;

  /* task depend(in:x) */
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_x1, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* task depend(in:x) */
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_y2, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* task depend(out:z) */
  { void *dep[] = { (void *)1, (void *)1, &z }; GOMP_task (tk_z3, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target map(tofrom:x) map(from:err) map(to:y,z) depend(inout:x,z) */
  { void *dep[] = { (void *)2, (void *)2, &x, &z }; GOMP_task (tgt_check1, NULL, NULL, 0, 0, false, DEP_FLAG, dep, 0, NULL); }
  if (err)
    abort ();

  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_x4, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_y5, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &z }; GOMP_task (tk_z6, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target enter data nowait map(to:w) -> no-op; target enter data depend -> no-op */
  /* target map(alloc:x,y,z) map(from:err) depend(inout:x,z) */
  { void *dep[] = { (void *)2, (void *)2, &x, &z }; GOMP_task (tgt_check2, NULL, NULL, 0, 0, false, DEP_FLAG, dep, 0, NULL); }
  if (err)
    abort ();
  GOMP_taskwait ();

  /* target map(alloc:w) map(from:err) */
  tgt_checkw (NULL);
  if (err)
    abort ();

  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_s14, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_t15, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &z }; GOMP_task (tk_u16, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target exit data depend -> no-op */
  GOMP_taskwait ();
  if (x != 7 || y != 8 || z != 9 || s != 14 || t != 15 || u != 16 || w != 17)
    abort ();
}

static void
par25 (void *d)
{
  (void) d;
  if (GOMP_single_start ())
    single25 (NULL);
  GOMP_barrier ();
}

int
main ()
{
  GOMP_parallel (par25, NULL, 0, 0);
  return 0;
}
