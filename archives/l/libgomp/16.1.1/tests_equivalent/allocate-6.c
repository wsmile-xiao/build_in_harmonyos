/* Equiv-rewrite of upstream allocate-6.c (run-time behavior only).
 *
 * #pragma omp allocate(iii,jjj,kkk,ptr) (no allocator clause) lowers to
 * GOMP_alloc(align,size,default-allocator)/GOMP_free. On host the default
 * allocator is the ordinary host allocator, so the value semantics are those
 * of firstprivate / target defaultmap(firstprivate|tofrom).
 */
#include <omp.h>
#include <stdlib.h>
#include <string.h>

extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void *GOMP_alloc (size_t, size_t, uintptr_t);
extern void GOMP_free (void *, uintptr_t);

static void
check_int (int *x, int y) { if (*x != y) __builtin_abort (); }
static void
check_ptr (int **x, int *y) { if (*x != y) __builtin_abort (); }

/* Body that reads the firstprivate values and then modifies them. */
struct bd { int *iii; int *jjj; int *kkk; int n; int **ptr; };
static void
body (void *p)
{
  struct bd *d = (struct bd *) p;
  if (*d->iii != 5) __builtin_abort ();
  *d->iii = 7;
  check_int (d->iii, 7);
  for (int i = 0; i < 5; i++)
    if (d->jjj[i] != 3 * i) __builtin_abort ();
  for (int i = 0; i < d->n; i++)
    if (d->kkk[i] != 7 * i) __builtin_abort ();
  for (int i = 0; i < 5; i++)
    d->jjj[i] = 4 * i;
  for (int i = 0; i < d->n; i++)
    d->kkk[i] = 8 * i;
  for (int i = 0; i < 5; i++)
    check_int (&d->jjj[i], 4 * i);
  for (int i = 0; i < d->n; i++)
    check_int (&d->kkk[i], 8 * i);
  if (*d->ptr != (int *) 0x1234) __builtin_abort ();
  *d->ptr = (int *) 0xabcd;
  if (*d->ptr != (int *) 0xabcd) __builtin_abort ();
  check_ptr (d->ptr, (int *) 0xabcd);
}

void
omp_parallel (void)
{
  int n = 6;
  omp_allocator_handle_t da = omp_get_default_allocator ();
  int *iii = GOMP_alloc (sizeof (int), sizeof (int), da);
  int *jjj = GOMP_alloc (sizeof (int), 5 * sizeof (int), da);
  int *kkk = GOMP_alloc (sizeof (int), (size_t) n * sizeof (int), da);
  int **ptr = GOMP_alloc (sizeof (int *), sizeof (int *), da);
  *iii = 5;
  *ptr = (int *) 0x1234;
  for (int i = 0; i < 5; i++) jjj[i] = 3 * i;
  for (int i = 0; i < n; i++) kkk[i] = 7 * i;

  /* parallel default(none) firstprivate(iii,jjj,kkk,ptr) if(0):
     serialized but a new task -> 1 thread on private copies. */
  {
    struct bd d = { iii, jjj, kkk, n, ptr };
    int ci = *iii, cj[5], ck[6], *cp = *ptr;
    memcpy (cj, jjj, sizeof cj);
    memcpy (ck, kkk, sizeof ck);
    struct bd dd = { &ci, cj, ck, n, &cp };
    GOMP_parallel (body, &dd, 1, 0);
  }
  if (*iii != 5) __builtin_abort ();
  check_int (iii, 5);
  for (int i = 0; i < 5; i++) { if (jjj[i] != 3 * i) __builtin_abort (); check_int (&jjj[i], 3 * i); }
  for (int i = 0; i < n; i++) { if (kkk[i] != 7 * i) __builtin_abort (); check_int (&kkk[i], 7 * i); }
  if (*ptr != (int *) 0x1234) __builtin_abort ();
  check_ptr (ptr, (int *) 0x1234);

  /* parallel default(firstprivate) if(0): same as above. */
  {
    int ci = *iii, cj[5], ck[6], *cp = *ptr;
    memcpy (cj, jjj, sizeof cj);
    memcpy (ck, kkk, sizeof ck);
    struct bd dd = { &ci, cj, ck, n, &cp };
    GOMP_parallel (body, &dd, 1, 0);
  }
  if (*iii != 5) __builtin_abort ();
  check_int (iii, 5);
  for (int i = 0; i < 5; i++) { if (jjj[i] != 3 * i) __builtin_abort (); check_int (&jjj[i], 3 * i); }
  for (int i = 0; i < n; i++) { if (kkk[i] != 7 * i) __builtin_abort (); check_int (&kkk[i], 7 * i); }
  if (*ptr != (int *) 0x1234) __builtin_abort ();
  check_ptr (ptr, (int *) 0x1234);

  GOMP_free (iii, da);
  GOMP_free (jjj, da);
  GOMP_free (kkk, da);
  GOMP_free (ptr, da);
}

void
omp_target (void)
{
  int n = 6;
  omp_allocator_handle_t da = omp_get_default_allocator ();
  int *iii = GOMP_alloc (sizeof (int), sizeof (int), da);
  int *jjj = GOMP_alloc (sizeof (int), 5 * sizeof (int), da);
  int *kkk = GOMP_alloc (sizeof (int), (size_t) n * sizeof (int), da);
  int **ptr = GOMP_alloc (sizeof (int *), sizeof (int *), da);
  *iii = 5;
  *ptr = (int *) 0x1234;
  for (int i = 0; i < 5; i++) jjj[i] = 3 * i;
  for (int i = 0; i < n; i++) kkk[i] = 7 * i;

  /* target firstprivate: copy in, no copy out (run on host). */
  {
    int ci = *iii, cj[5], ck[6], *cp = *ptr;
    memcpy (cj, jjj, sizeof cj);
    memcpy (ck, kkk, sizeof ck);
    struct bd dd = { &ci, cj, ck, n, &cp };
    body (&dd);
  }
  if (*iii != 5) __builtin_abort ();
  for (int i = 0; i < 5; i++) { if (jjj[i] != 3 * i) __builtin_abort (); check_int (&jjj[i], 3 * i); }
  for (int i = 0; i < n; i++) { if (kkk[i] != 7 * i) __builtin_abort (); check_int (&kkk[i], 7 * i); }
  if (*ptr != (int *) 0x1234) __builtin_abort ();

  /* target defaultmap(firstprivate): copy in, no copy out. */
  {
    int ci = *iii, cj[5], ck[6], *cp = *ptr;
    memcpy (cj, jjj, sizeof cj);
    memcpy (ck, kkk, sizeof ck);
    struct bd dd = { &ci, cj, ck, n, &cp };
    body (&dd);
  }
  if (*iii != 5) __builtin_abort ();
  for (int i = 0; i < 5; i++) { if (jjj[i] != 3 * i) __builtin_abort (); check_int (&jjj[i], 3 * i); }
  for (int i = 0; i < n; i++) { if (kkk[i] != 7 * i) __builtin_abort (); check_int (&kkk[i], 7 * i); }
  if (*ptr != (int *) 0x1234) __builtin_abort ();

  /* target defaultmap(tofrom): copy in + copy out -> modifications propagate. */
  {
    struct bd dd = { iii, jjj, kkk, n, ptr };
    body (&dd);
  }
  if (*iii != 7) __builtin_abort ();
  check_int (iii, 7);
  for (int i = 0; i < 5; i++) { if (jjj[i] != 4 * i) __builtin_abort (); check_int (&jjj[i], 4 * i); }
  for (int i = 0; i < n; i++) { if (kkk[i] != 8 * i) __builtin_abort (); check_int (&kkk[i], 8 * i); }
  if (*ptr != (int *) 0xabcd) __builtin_abort ();
  check_ptr (ptr, (int *) 0xabcd);

  GOMP_free (iii, da);
  GOMP_free (jjj, da);
  GOMP_free (kkk, da);
  GOMP_free (ptr, da);
}

int
main (void)
{
  omp_parallel ();
  omp_target ();
  return 0;
}
