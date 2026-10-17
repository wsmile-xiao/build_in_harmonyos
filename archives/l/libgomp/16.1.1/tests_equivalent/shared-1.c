/* Equiv-rewrite of upstream shared-1.c.
 * #pragma omp parallel shared(a,b,A) num_threads(5) -> GOMP_parallel + data
 *   struct with pointers to shared a/b and the shared array A.
 * #pragma omp atomic -> GOMP_atomic_start/end.
 * #pragma omp for private(j) -> GOMP_loop_static_* (result is schedule-independent).
 */
#include <omp.h>

extern void abort (void);
extern int omp_get_num_threads (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern _Bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern _Bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

struct Y { int l[5][10]; };
struct X { struct Y y; float b[10]; };

struct s_data { int *a; int *b; struct X (*A)[5]; };

static void s_body (void *p)
{
  struct s_data *d = (struct s_data *) p;
  int i, j;                 /* i loop var (private), j private */
  long istart, iend;

  GOMP_atomic_start ();
  *d->a += omp_get_num_threads ();
  GOMP_atomic_end ();

  GOMP_atomic_start ();
  *d->b += omp_get_num_threads ();
  GOMP_atomic_end ();

  if (GOMP_loop_static_start (0, 10, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = (int) istart; i < (int) iend; i++)
	    for (j = 0; j < 5; j++)
	      d->A[i][j].y.l[3][3] += 20;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

void parallel (int a, int b)
{
  int i, j;
  struct X A[10][5];
  struct s_data d = { &a, &b, A };
  a = b = 3;

  for (i = 0; i < 10; i++)
    for (j = 0; j < 5; j++)
      A[i][j].y.l[3][3] = -10;

  GOMP_parallel (s_body, &d, 5, 0);

  for (i = 0; i < 10; i++)
    for (j = 0; j < 5; j++)
      if (A[i][j].y.l[3][3] != 10)
	abort ();

  if (a != 28)
    abort ();
  if (b != 28)
    abort ();
}

int main (void)
{
  parallel (1, 2);
  return 0;
}
