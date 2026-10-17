#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdint.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_single_start (void);
void GOMP_task (void (*)(void *), void *, void (*)(void *, void *), long, long, bool, unsigned, void **, int, void *);
void GOMP_atomic_start (void);
void GOMP_atomic_end (void);
void GOMP_barrier (void);

#define DEP_FLAG 8

static int a, b, c, d[7];

static void noop (void *dd) { (void) dd; }
static void tk_a2 (void *dd) { (void) dd; a = 2; }
static void tk_ainc (void *dd) { (void) dd; a++; }
static void tk_b4 (void *dd) { (void) dd; usleep (1000); GOMP_atomic_start (); b |= 4; GOMP_atomic_end (); }
static void tk_b1 (void *dd) { (void) dd; usleep (5000); GOMP_atomic_start (); b |= 1; GOMP_atomic_end (); }
static void tk_c8 (void *dd) { (void) dd; usleep (5000); GOMP_atomic_start (); c |= 8; GOMP_atomic_end (); }
static void tk_c2 (void *dd) { (void) dd; usleep (1000); GOMP_atomic_start (); c |= 2; GOMP_atomic_end (); }

static void
single32 (void *dd)
{
  (void) dd;

  /* task depend(out:d[0]) a = 2 */
  { void *dep[] = { (void *)1, (void *)1, &d[0] }; GOMP_task (tk_a2, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target enter data nowait depend(in:d[0]) depend(out:d[1]) -> bridge task */
  { void *dep[] = { (void *)2, (void *)1, &d[1], &d[0] }; GOMP_task (noop, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target nowait depend(in:d[1]) depend(out:d[2]) a++ */
  { void *dep[] = { (void *)2, (void *)1, &d[2], &d[1] }; GOMP_task (tk_ainc, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target nowait depend(in:d[2]) depend(out:d[3]) b|=4 */
  { void *dep[] = { (void *)2, (void *)1, &d[3], &d[2] }; GOMP_task (tk_b4, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target nowait depend(in:d[2]) depend(out:d[4]) b|=1 */
  { void *dep[] = { (void *)2, (void *)1, &d[4], &d[2] }; GOMP_task (tk_b1, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target nowait depend(in:d[3],d[4]) depend(out:d[5]) c|=8 */
  { void *dep[] = { (void *)3, (void *)1, &d[5], &d[3], &d[4] }; GOMP_task (tk_c8, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target nowait depend(in:d[3],d[4]) depend(out:d[6]) c|=2 */
  { void *dep[] = { (void *)3, (void *)1, &d[6], &d[3], &d[4] }; GOMP_task (tk_c2, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target exit data depend(in:d[5],d[6]) -> bridge task */
  { void *dep[] = { (void *)2, (void *)0, &d[5], &d[6] }; GOMP_task (noop, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
}

static void
par32 (void *dd)
{
  (void) dd;
  if (GOMP_single_start ())
    single32 (NULL);
  GOMP_barrier ();
}

int
main ()
{
  GOMP_parallel (par32, NULL, 0, 0);
  if (a != 3 || b != 5 || c != 10)
    abort ();
  return 0;
}
