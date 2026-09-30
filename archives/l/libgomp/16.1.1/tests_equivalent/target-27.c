#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdint.h>

void GOMP_parallel (void (*)(void *), void *, unsigned, unsigned);
bool GOMP_single_start (void);
void GOMP_task (void (*)(void *), void *, void (*)(void *, void *), long, long, bool, unsigned, void **, int, void *);
void GOMP_taskwait (void);
void GOMP_barrier (void);

#define DEP_FLAG 8

static int x, y, z, err;
static int shared_mem;

static void tk_x1 (void *d) { (void)d; usleep (5000); x = 1; }
static void tk_y2 (void *d) { (void)d; usleep (6000); y = 2; }
static void tk_z3 (void *d) { (void)d; usleep (7000); z = 3; }
static void tk_xyz (void *d) { (void)d; x++; y++; z++; }
static void tgt_check (void *d) { (void)d; err = (x != 2 || y != 3 || z != 4); x = 5; y = 6; z = 7; }
static void tk_nx (void *d) { (void)d; usleep (5000); if (!shared_mem) x = 1; }
static void tk_ny (void *d) { (void)d; usleep (6000); if (!shared_mem) y = 2; }
static void tk_nz (void *d) { (void)d; usleep (3000); if (!shared_mem) z = 3; }

static void
single27 (void *d)
{
  (void) d;

  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_x1, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_y2, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)1, &z }; GOMP_task (tk_z3, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target enter/update data are host no-ops; the remaining dependency
     chain reduces to the inout:x,z tasks below.  */
  { void *dep[] = { (void *)2, (void *)2, &x, &z }; GOMP_task (tk_xyz, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)2, (void *)2, &x, &z }; GOMP_task (tgt_check, NULL, NULL, 0, 0, false, DEP_FLAG, dep, 0, NULL); }
  if (err)
    abort ();

  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_nx, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)0, &x }; GOMP_task (tk_ny, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  { void *dep[] = { (void *)1, (void *)1, &z }; GOMP_task (tk_nz, NULL, NULL, 0, 0, true, DEP_FLAG, dep, 0, NULL); }
  /* target exit data are host no-ops */
  GOMP_taskwait ();
  if (err || x != 5 || y != 6 || z != 7)
    abort ();
}

static void
par27 (void *d)
{
  (void) d;
  if (GOMP_single_start ())
    single27 (NULL);
  GOMP_barrier ();
}

int
main ()
{
  /* target map(to:shared_mem): host fallback -> shared_mem = 1 */
  shared_mem = 1;
  GOMP_parallel (par27, NULL, 0, 0);
  return 0;
}
