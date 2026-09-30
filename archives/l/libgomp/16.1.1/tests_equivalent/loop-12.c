/* Equiv-rewrite of upstream loop-12.c (same semantics as loop-6.c; only the
 * reversed relational forms differ, denoting identical iteration sets).
 */
#include <stdlib.h>
#include <omp.h>
#include "b2g2_common.h"

extern void abort (void);

#define LLONG_MAX __LONG_LONG_MAX__
#define ULLONG_MAX (LLONG_MAX * 2ULL + 1)
#define INT_MAX __INT_MAX__

int arr[6 * 5];

static void
set (int loopidx, int idx)
{
  __atomic_fetch_add (&arr[loopidx * 5 + idx], 1, __ATOMIC_SEQ_CST);
}

#define test(loopidx, count) \
  for (idx = 0; idx < 5; idx++) \
    if (arr[loopidx * 5 + idx] != idx < count) \
      abort (); \
    else \
      arr[loopidx * 5 + idx] = 0

struct ectx { int *e; };

static void l1 (void *ctx, long ii) { struct ectx *c = ctx; long long i = (long long) ii;
  if (i == LLONG_MAX - 30001) set (0, 0);
  else if (i == LLONG_MAX - 20001) set (0, 1);
  else if (i == LLONG_MAX - 10001) set (0, 2);
  else *c->e = 1; }

static void l2 (void *ctx, long ii) { struct ectx *c = ctx; long long i = (long long) ii;
  if (i == -LLONG_MAX + 30000) set (1, 0);
  else if (i == -LLONG_MAX + 20000) set (1, 1);
  else if (i == -LLONG_MAX + 10000) set (1, 2);
  else *c->e = 1; }

static void l3 (void *ctx, unsigned long long jj) { struct ectx *c = ctx;
  if (jj == 20) set (2, 0); else *c->e = 1; }

static void l4 (void *ctx, unsigned long long jj) { struct ectx *c = ctx;
  if (jj == ULLONG_MAX - 3) set (3, 0); else *c->e = 1; }

static void l5 (void *ctx, unsigned long long jj) { struct ectx *c = ctx;
  if (jj == LLONG_MAX - 20000ULL) set (4, 0);
  else if (jj == LLONG_MAX - 10000ULL) set (4, 1);
  else if (jj == LLONG_MAX) set (4, 2);
  else if (jj == LLONG_MAX + 10000ULL) set (4, 3);
  else *c->e = 1; }

static void l6 (void *ctx, long ii) { struct ectx *c = ctx; long long i = (long long) ii;
  if (i == -3LL * INT_MAX - 20000LL) set (5, 0);
  else if (i == -2LL * INT_MAX - 20000LL + 200LL) set (5, 1);
  else if (i == -INT_MAX - 20000LL + 400LL) set (5, 2);
  else if (i == -20000LL + 600LL) set (5, 3);
  else if (i == INT_MAX - 20000LL + 800LL) set (5, 4);
  else *c->e = 1; }

struct data { int sched; long chunk; int *e; };

static void
body (void *p)
{
  struct data *d = (struct data *) p;
  int tid = omp_get_thread_num ();
  int el = 0;
  struct ectx ec = { &el };
  int s = d->sched;
  long ch = d->chunk;
  unsigned long long uchs = (unsigned long long) (ch < 0 ? 0 : ch);

  struct b2g2_ws w1 = { &ec, l1, s, LLONG_MAX - 30001, LLONG_MAX - 10000, 10000, ch };
  struct b2g2_ws w2 = { &ec, l2, s, -LLONG_MAX + 30000, -LLONG_MAX + 0, -10000, ch };
  struct b2g2_ws_ull w3 = { &ec, l3, s, 20ULL, LLONG_MAX - 69ULL, LLONG_MAX + 50ULL, uchs };
  struct b2g2_ws_ull w4 = { &ec, l4, s, ULLONG_MAX - 3ULL, ULLONG_MAX - 2ULL, 1ULL, uchs };
  struct b2g2_ws_ull w5 = { &ec, l5, s, LLONG_MAX - 20000ULL, LLONG_MAX + 10001ULL, 10000ULL, uchs };
  struct b2g2_ws w6 = { &ec, l6, s, -3LL * INT_MAX - 20000LL, INT_MAX + 10000LL + 1, INT_MAX + 200LL, ch };

  b2g2_ws (&w1, 1);
  b2g2_ws (&w2, 1);
  b2g2_ws_ull (&w3, 1);
  b2g2_ws_ull (&w4, 1);
  b2g2_ws_ull (&w5, 1);
  b2g2_ws (&w6, 1);

  d->e[tid] = el;
}

static void
run_test (int sched, long chunk)
{
  int e = 0, idx;
  int nt = omp_get_max_threads ();
  int *earr = (int *) calloc ((size_t) nt, sizeof (int));
  struct data d = { sched, chunk, earr };
  int t;

  GOMP_parallel (body, &d, 0, 0);

  for (t = 0; t < nt; t++)
    e += earr[t];
  free (earr);

  if (e)
    abort ();
  test (0, 3);
  test (1, 3);
  test (2, 1);
  test (3, 1);
  test (4, 4);
  test (5, 5);
}

int
main (void)
{
  if (2 * sizeof (int) != sizeof (long long))
    return 0;
  run_test (1, 1);
  run_test (2, 1);
  run_test (0, 0);
  run_test (0, 1);
  omp_set_schedule (omp_sched_static, 0);
  run_test (3, 0);
  omp_set_schedule (omp_sched_static, 3);
  run_test (3, 0);
  omp_set_schedule (omp_sched_dynamic, 5);
  run_test (3, 0);
  omp_set_schedule (omp_sched_guided, 2);
  run_test (3, 0);
  return 0;
}
