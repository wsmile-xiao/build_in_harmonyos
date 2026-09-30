extern void abort (void);
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

void GOMP_task (void (*)(void *), void *, void (*)(void *, void *), long, long, bool, unsigned, void **, int, void *);
void GOMP_taskwait (void);
void GOMP_taskgroup_start (void);
void GOMP_taskgroup_end (void);
void GOMP_atomic_start (void);
void GOMP_atomic_end (void);
void GOMP_barrier (void);

#define DEP_FLAG 8

static int a = 1, b = 2, c = 4, d[7];

static void noop (void *dd) { (void) dd; }
static void t1 (void *dd) { (void) dd; GOMP_atomic_start (); a |= 4; GOMP_atomic_end (); GOMP_atomic_start (); b |= 8; GOMP_atomic_end (); }
static void t2 (void *dd) { (void) dd; GOMP_atomic_start (); a |= 16; GOMP_atomic_end (); GOMP_atomic_start (); c |= 32; GOMP_atomic_end (); }
static void t3 (void *dd) { (void) dd; a &= ~16; b &= ~2; }
static void t4 (void *dd) { (void) dd; c |= 8; }
static void t5 (void *dd) { (void) dd; a |= 32; b |= 4; }
static void t6 (void *dd) { (void) dd; c &= ~4; }
static void t7 (void *dd) { (void) dd; GOMP_atomic_start (); a = a + 9; GOMP_atomic_end (); b -= 8; }
static void t8 (void *dd) { (void) dd; GOMP_atomic_start (); a = a + 4; GOMP_atomic_end (); c >>= 1; }
static void t9 (void *dd) { (void) dd; if (a != 50 || b != 4 || c != 20) abort (); }
static void t10 (void *dd) { (void) dd; a += 50; }
static void t11 (void *dd) { (void) dd; b++; }
static void t12 (void *dd) { (void) dd; c--; }
static void t13 (void *dd) { (void) dd; a++; }
static void t14 (void *dd) { (void) dd; b++; }
static void t15 (void *dd) { (void) dd; if (a != 101 || b != 6) a = -9; else { a = 24; b = 38; } }

int
main ()
{
  GOMP_taskgroup_start ();
  { void *dep[] = { (void *)1, (void *)1, &d[0] }; GOMP_task (noop, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)1, &d[1], &d[0] }; GOMP_task (t1, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)1, &d[2], &d[0] }; GOMP_task (t2, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)0, &d[1], &d[2] }; GOMP_task (noop, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  GOMP_taskgroup_end ();
  if (a != 21 || b != 10 || c != 36)
    abort ();

  GOMP_task (t3, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_task (t4, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_barrier ();
  if (a != 5 || b != 8 || c != 44)
    abort ();

  GOMP_task (t5, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_task (t6, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_taskwait ();
  if (a != 37 || b != 12 || c != 40)
    abort ();

  { void *dep[] = { (void *)1, (void *)1, &d[3] }; GOMP_task (t7, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)1, &d[4] }; GOMP_task (t8, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)0, &d[3], &d[4] }; GOMP_task (t9, NULL, NULL, 0, 0, false, DEP_FLAG, dep, 0, NULL); }
  GOMP_task (t10, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_task (t11, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_task (t12, NULL, NULL, 0, 0, true, 0, NULL, 0, NULL);
  GOMP_taskwait ();
  if (a != 100 || b != 5 || c != 19)
    abort ();

  { void *dep[] = { (void *)1, (void *)1, &d[5] }; GOMP_task (t13, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)1, &d[6] }; GOMP_task (t14, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)0, &d[5], &d[6] }; GOMP_task (t15, NULL, NULL, 0, 0, false, DEP_FLAG, dep, 0, NULL); }
  if (a != 24 || b != 38)
    abort ();
  return 0;
}
