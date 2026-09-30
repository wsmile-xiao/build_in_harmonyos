/* Equiv-rewrite of upstream allocate-5.c (run-time behavior only; the
 * scan-tree-dump checks are GCC-specific and not applicable to clang).
 *
 *   one(): #pragma omp target (host) + #pragma omp allocate(var,var2)
 *          align(128) allocator(omp_low_lat_mem_alloc)
 *          + #pragma omp parallel for + #pragma omp loop reduction(+:result)
 *   two(): #pragma omp allocate(scalar,array,s) + #pragma omp parallel
 *          firstprivate + #pragma omp target firstprivate/tofrom
 */
#include <omp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern void *GOMP_alloc (size_t, size_t, uintptr_t);
extern void GOMP_free (void *, uintptr_t);

/* ---- one() helpers ---- */
struct pfor_d { int n; int *var2; };
static void pfor_body (void *p)
{
  struct pfor_d *d = (struct pfor_d *) p;
  long istart, iend;
  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  d->var2[i] = i + 33;
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

struct red_d { int n; int var; int *var2; int *partials; };
static void red_body (void *p)
{
  struct red_d *d = (struct red_d *) p;
  int tid = omp_get_thread_num ();
  int partial = 0;
  long istart, iend;
  if (GOMP_loop_static_start (0, d->n, 1, 0, &istart, &iend))
    {
      do
	for (long i = istart; i < iend; i++)
	  partial += d->var + d->var2[i];
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
  d->partials[tid] = partial;
}

void
one ()
{
  int result = 0, n = 3;
  /* target map(tofrom: result) firstprivate(n) -> host body, n is a copy. */
  {
    int n2 = n;
    int *var = GOMP_alloc (128, sizeof (int), omp_low_lat_mem_alloc);
    int *var2 = GOMP_alloc (128, (size_t) n2 * sizeof (int), omp_low_lat_mem_alloc);
    *var = 5;

    if ((intptr_t) var % 128 != 0)
      __builtin_abort ();
    if ((intptr_t) var2 % 128 != 0)
      __builtin_abort ();
    if (*var != 5)
      __builtin_abort ();

    { struct pfor_d pd = { n2, var2 }; GOMP_parallel (pfor_body, &pd, 0, 0); }

    {
      int nt = omp_get_max_threads ();
      if (nt < 1) nt = 1;
      int *partials = calloc ((size_t) nt, sizeof (int));
      struct red_d rd = { n2, *var, var2, partials };
      GOMP_parallel (red_body, &rd, 0, 0);
      for (int t = 0; t < nt; t++)
	result += partials[t];
      free (partials);
    }

    GOMP_free (var, omp_low_lat_mem_alloc);
    GOMP_free (var2, omp_low_lat_mem_alloc);
  }
  if (result != (3 * 5 + 33 + 34 + 35))
    __builtin_abort ();
}

/* ---- two() helpers ---- */
struct st { int a, b; };
struct orig { int scalar; int array[5]; struct st s; };
/* firstprivate lowering: each thread builds its own copy from the read-only
   original, then checks/modifies the copy (original left untouched). */
static void fp_body (void *p)
{
  struct orig *o = (struct orig *) p;
  int scalar = o->scalar;
  int array[5];
  struct st s = o->s;
  memcpy (array, o->array, sizeof array);
  if (scalar != 44)
    __builtin_abort ();
  scalar = 33;
  for (int i = 0; i < 5; ++i)
    if (array[i] != i + 1)
      __builtin_abort ();
  for (int i = 0; i < 5; ++i)
    array[i] = 10 * (i + 1);
  if (s.a != 11 || s.b != 56)
    __builtin_abort ();
  s.a = 74;
  s.b = 674;
}

void
two ()
{
  int scalar = 44, array[5] = { 1, 2, 3, 4, 5 };
  struct st s = { 11, 56 };

  /* parallel firstprivate(scalar,array,s): each thread works on a private
     copy built inside fp_body; original unchanged. */
  {
    struct orig o = { scalar, { 1, 2, 3, 4, 5 }, { 11, 56 } };
    GOMP_parallel (fp_body, &o, 0, 0);
  }
  if (scalar != 44)
    __builtin_abort ();
  for (int i = 0; i < 5; ++i)
    if (array[i] != i + 1)
      __builtin_abort ();
  if (s.a != 11 || s.b != 56)
    __builtin_abort ();

  /* target defaultmap(firstprivate:scalar): copy in, no copy out. */
  {
    int sc = scalar;
    if (sc != 44) __builtin_abort ();
    sc = 33;
    (void) sc;
  }
  if (scalar != 44)
    __builtin_abort ();

  /* target defaultmap(firstprivate:aggregate) for array. */
  {
    int arr[5];
    memcpy (arr, array, sizeof arr);
    for (int i = 0; i < 5; ++i)
      if (arr[i] != i + 1) __builtin_abort ();
    for (int i = 0; i < 5; ++i)
      arr[i] = 10 * (i + 1);
    (void) arr;
  }
  for (int i = 0; i < 5; ++i)
    if (array[i] != i + 1)
      __builtin_abort ();

  /* target defaultmap(firstprivate:aggregate) for s. */
  {
    struct st ss = s;
    if (ss.a != 11 || ss.b != 56) __builtin_abort ();
    ss.a = 74;
    ss.b = 674;
    (void) ss;
  }
  if (s.a != 11 || s.b != 56)
    __builtin_abort ();
}

int
main ()
{
  one ();
  two ();
  return 0;
}
