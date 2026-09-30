/* affinity-1.c — 完全等价改写 (OMP_PROC_BIND=false, host 退化)
 *
 * aarch64/OHOS 上: config.h 未定义 HAVE_PTHREAD_AFFINITY_NP → print_affinity 为 no-op；
 * 未定义 DO_FORK → fork 段裁剪。因此原测试在真机上唯一运行时断言是:
 *   OMP_PROC_BIND=false 下，所有(嵌套)parallel 区域内 omp_get_proc_bind()==false。
 *
 * 全部 #pragma omp parallel [proc_bind] → GOMP_parallel(proc_bind 子句 host 上退化丢弃)，
 * critical → GOMP_critical_start/end, barrier → GOMP_barrier, if(0) → num_threads=1。
 * firstprivate(pp) → 结构体传值。
 */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_barrier (void);
extern void GOMP_critical_start (void);
extern void GOMP_critical_end (void);

static void
check_bind (void)
{
  if (omp_get_proc_bind () != omp_proc_bind_false)
    abort ();
}

struct ppd
{
  int pp;
};

/* ---- forward decls ---- */
static void A_fn (void *);
static void A1_fn (void *);
static void A1a_fn (void *);
static void A1b_fn (void *);
static void A2_fn (void *);
static void A2a_fn (void *);
static void A2b_fn (void *);
static void B_fn (void *);
static void B1_fn (void *);
static void B2_fn (void *);
static void B2a_fn (void *);
static void B3_fn (void *);
static void B4_fn (void *);
static void C_fn (void *);
static void C1_fn (void *);
static void C2_fn (void *);
static void C3_fn (void *);
static void C4_fn (void *);
static void D_fn (void *);
static void D1_fn (void *);
static void D2_fn (void *);
static void D2a_fn (void *);
static void D2b_fn (void *);
static void D3_fn (void *);
static void D4_fn (void *);
static void E_fn (void *);
static void E1_fn (void *);
static void E2_fn (void *);
static void E2a_fn (void *);
static void E2b_fn (void *);
static void E2c_fn (void *);
static void E3_fn (void *);
static void E4_fn (void *);

/* ---- A: parallel if(0) ---- */
static void
A_fn (void *d)
{
  check_bind ();
  GOMP_parallel (A1_fn, NULL, 1, 0);
  GOMP_parallel (A2_fn, NULL, 1, 0);
}

static void
A1_fn (void *d)
{
  check_bind ();
  GOMP_parallel (A1a_fn, NULL, 1, 0);
  GOMP_parallel (A1b_fn, NULL, 1, 0);
}

static void A1a_fn (void *d) { check_bind (); }
static void A1b_fn (void *d) { check_bind (); }

static void
A2_fn (void *d)
{
  check_bind ();
  GOMP_parallel (A2a_fn, NULL, 1, 0);
  GOMP_parallel (A2b_fn, NULL, 1, 0);
}

static void A2a_fn (void *d) { check_bind (); }
static void A2b_fn (void *d) { check_bind (); }

/* ---- B: parallel num_threads(4) ---- */
static void
B_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 3)
    {
      GOMP_parallel (B1_fn, NULL, 3, 0);
      GOMP_parallel (B2_fn, NULL, 5, 0);
      GOMP_parallel (B3_fn, NULL, 4, 0);
      GOMP_parallel (B4_fn, NULL, 6, 0);
    }
}

static void
B1_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
B2_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 3)
    GOMP_parallel (B2a_fn, NULL, 5, 0);
}

static void
B2a_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
B3_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
B4_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

/* ---- C: parallel num_threads(5) proc_bind(spread) ---- */
static void
C_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 3)
    {
      int pp = 0;
      struct ppd p;
      p.pp = pp;
      GOMP_parallel (C1_fn, &p, 3, 0);
      GOMP_parallel (C2_fn, &p, 5, 0);
      GOMP_parallel (C3_fn, &p, 4, 0);
      GOMP_parallel (C4_fn, &p, 6, 0);
    }
}

static void
C1_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
C2_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
C3_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
C4_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

/* ---- D: parallel num_threads(3) proc_bind(master) ---- */
static void
D_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 2)
    {
      GOMP_parallel (D1_fn, NULL, 4, 0);
      GOMP_parallel (D2_fn, NULL, 4, 0);
      GOMP_parallel (D3_fn, NULL, 4, 0);
      GOMP_parallel (D4_fn, NULL, 6, 0);
    }
}

static void
D1_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
D2_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 0)
    GOMP_parallel (D2a_fn, NULL, 5, 0);
  GOMP_barrier ();
  if (omp_get_thread_num () == 3)
    GOMP_parallel (D2b_fn, NULL, 5, 0);
}

static void
D2a_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
D2b_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
D3_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
D4_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

/* ---- E: parallel num_threads(5) proc_bind(close) ---- */
static void
E_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 2)
    {
      int pp = 0;
      struct ppd p;
      p.pp = pp;
      GOMP_parallel (E1_fn, &p, 4, 0);
      GOMP_parallel (E2_fn, NULL, 4, 0);
      GOMP_parallel (E3_fn, &p, 4, 0);
      GOMP_parallel (E4_fn, NULL, 6, 0);
    }
}

static void
E1_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
E2_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
  GOMP_barrier ();
  if (omp_get_thread_num () == 0)
    GOMP_parallel (E2a_fn, NULL, 5, 0);
  GOMP_barrier ();
  if (omp_get_thread_num () == 2)
    GOMP_parallel (E2b_fn, NULL, 5, 0);
  GOMP_barrier ();
  if (omp_get_thread_num () == 3)
    GOMP_parallel (E2c_fn, NULL, 5, 0);
}

static void
E2a_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
E2b_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
E2c_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
E3_fn (void *d)
{
  int pp = ((struct ppd *) d)->pp;
  (void) pp;
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

static void
E4_fn (void *d)
{
  check_bind ();
  GOMP_critical_start ();
  GOMP_critical_end ();
}

int
main (void)
{
  if (omp_proc_bind_master != omp_proc_bind_primary)
    abort ();

  omp_set_nested (1);
  omp_set_dynamic (0);

  GOMP_parallel (A_fn, NULL, 1, 0);	/* parallel if(0) */
  GOMP_parallel (B_fn, NULL, 4, 0);
  GOMP_parallel (C_fn, NULL, 5, 0);
  GOMP_parallel (D_fn, NULL, 3, 0);
  GOMP_parallel (E_fn, NULL, 5, 0);

  return 0;
}
