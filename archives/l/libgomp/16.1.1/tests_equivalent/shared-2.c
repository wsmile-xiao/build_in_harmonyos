/* shared-2.c — 完全等价改写
 * parallel firstprivate(a,b) shared(bad) num_threads(5)
 *   + for lastprivate(LASTPRIV) + sections lastprivate(LASTPRIV_SEC) → GOMP ABI。
 */
#include <stdlib.h>
#include <stdbool.h>

extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern bool GOMP_loop_static_start (long, long, long, long, long *, long *);
extern bool GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);
extern unsigned GOMP_sections_start (unsigned);
extern unsigned GOMP_sections_next (void);
extern void GOMP_sections_end (void);

struct pd
{
  int a, b;		/* firstprivate */
  int *bad;		/* shared */
  int *LASTPRIV;	/* shared (for lastprivate) */
  int *LASTPRIV_SEC;	/* shared (sections lastprivate) */
};

static void
pfn (void *arg)
{
  struct pd *d = (struct pd *) arg;
  int a = d->a, b = d->b;	/* firstprivate copies */
  int i;
  long istart, iend;
  unsigned s;

  if (a != 3 || b != 3)
    *d->bad = 1;

  /* for lastprivate(LASTPRIV): 最后一个 chunk 写回最后一轮的值(9) */
  if (GOMP_loop_static_start (0, 10, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    ;			/* LASTPRIV = i (每线程私有) */
	  if (iend == 10)
	    *d->LASTPRIV = iend - 1;
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* sections lastprivate(LASTPRIV_SEC): 最后一个 section(42) 写回 */
  for (s = GOMP_sections_start (2); s != 0; s = GOMP_sections_next ())
    {
      if (s == 1)
	{
	  int tmp = 3;		/* 非最后 section，私有丢弃 */
	  (void) tmp;
	}
      else if (s == 2)
	*d->LASTPRIV_SEC = 42;
    }
  GOMP_sections_end ();
}

void
parallel (int a, int b)
{
  int bad, LASTPRIV, LASTPRIV_SEC;
  a = b = 3;
  bad = 0;
  struct pd d = { a, b, &bad, &LASTPRIV, &LASTPRIV_SEC };
  GOMP_parallel (pfn, &d, 5, 0);

  if (LASTPRIV != 9)
    abort ();
  if (LASTPRIV_SEC != 42)
    abort ();
  if (bad)
    abort ();
}

int
main (void)
{
  parallel (1, 2);
  return 0;
}
