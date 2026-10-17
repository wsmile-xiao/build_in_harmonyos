/* Equiv-rewrite of upstream reduction-15.c: parallel + 4 worksharing for-loops with reductions. */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern int GOMP_loop_static_start (long, long, long, long, long *, long *);
extern int GOMP_loop_static_next (long *, long *);
extern int GOMP_loop_guided_start (long, long, long, long, long *, long *);
extern int GOMP_loop_guided_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 64

int a[16], b[16], c[16], d[5][2];

static int g_nt;
static int priv_a[MAXT][3];
static int priv_b[MAXT][3];
static int priv_c[MAXT][4];
static int priv_d[MAXT][2][2];

__attribute__((noinline, noclone)) static void
foo (int x, int y)
{
  int tn = omp_get_thread_num ();
  int i, e;
  long istart, iend;
  (void) x; (void) y;
  g_nt = omp_get_num_threads ();

  /* for schedule(static,1) reduction(+:a[:3]) */
  for (e = 0; e < 3; e++) priv_a[tn][e] = 0;
  if (GOMP_loop_static_start (0, 64, 1, 1, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      priv_a[tn][0] += i;
	      priv_a[tn][1] += 2 * i;
	      priv_a[tn][2] += 3 * i;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* for schedule(guided) reduction(+:b[4:3]) */
  for (e = 0; e < 3; e++) priv_b[tn][e] = 0;
  if (GOMP_loop_guided_start (0, 64, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      priv_b[tn][0] += i;
	      priv_b[tn][1] += 2 * i;
	      priv_b[tn][2] += 3 * i;
	    }
	}
      while (GOMP_loop_guided_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* for schedule(static) reduction(+:c[x:4]) with x == 9 */
  for (e = 0; e < 4; e++) priv_c[tn][e] = 0;
  if (GOMP_loop_static_start (0, 64, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      priv_c[tn][0] += i;
	      priv_c[tn][1] += 2 * i;
	      priv_c[tn][2] += 3 * i;
	      priv_c[tn][3] += 4 * i;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();

  /* for reduction(+:d[x-8:2][y:]) with x==9,y==0 => d[1:2][0:2] */
  for (e = 0; e < 2; e++)
    {
      priv_d[tn][e][0] = 0;
      priv_d[tn][e][1] = 0;
    }
  if (GOMP_loop_static_start (0, 64, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      priv_d[tn][0][0] += i;
	      priv_d[tn][0][1] += 2 * i;
	      priv_d[tn][1][0] += 3 * i;
	      priv_d[tn][1][1] += 4 * i;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

static void
parallel_body (void *p)
{
  (void) p;
  foo (9, 0);
}

int
main ()
{
  int i, t, e;
  GOMP_parallel (parallel_body, 0, 0, 0);

  for (e = 0; e < 3; e++)
    {
      int s = a[e];
      for (t = 0; t < g_nt; t++) s += priv_a[t][e];
      a[e] = s;
    }
  for (e = 0; e < 3; e++)
    {
      int s = b[e + 4];
      for (t = 0; t < g_nt; t++) s += priv_b[t][e];
      b[e + 4] = s;
    }
  for (e = 0; e < 4; e++)
    {
      int s = c[e + 9];
      for (t = 0; t < g_nt; t++) s += priv_c[t][e];
      c[e + 9] = s;
    }
  for (e = 0; e < 2; e++)
    {
      int s0 = d[e + 1][0];
      int s1 = d[e + 1][1];
      for (t = 0; t < g_nt; t++)
	{
	  s0 += priv_d[t][e][0];
	  s1 += priv_d[t][e][1];
	}
      d[e + 1][0] = s0;
      d[e + 1][1] = s1;
    }

  for (i = 0; i < 16; i++)
    if (a[i] != (i < 3 ? 64 * 63 / 2 * (i + 1) : 0)
	|| b[i] != ((i >= 4 && i < 7) ? 64 * 63 / 2 * (i - 3) : 0)
	|| c[i] != ((i >= 9 && i < 13) ? 64 * 63 / 2 * (i - 8) : 0))
      abort ();
  for (i = 0; i < 5; i++)
    if (d[i][0] != ((i && i <= 2) ? 64 * 63 / 2 * (2 * i - 1) : 0)
	|| d[i][1] != ((i && i <= 2) ? 64 * 63 / 2 * (2 * i) : 0))
      abort ();
  return 0;
}
