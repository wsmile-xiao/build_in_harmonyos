/* Equiv-rewrite of upstream reduction-9.c: variable-size array-section reductions. */
#include <omp.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>

extern void GOMP_parallel (void (*)(void*), void *, unsigned, unsigned);
extern int GOMP_loop_static_start (long, long, long, long, long *, long *);
extern int GOMP_loop_static_next (long *, long *);
extern void GOMP_loop_end (void);

#define MAXT 64

char z[10] = { 0 };

static int g_nt;
static int priv_x[MAXT][12];
static char priv_z[MAXT][4];
static int priv_y[MAXT][3];
static unsigned long long priv_a[MAXT][4];
static long priv_w[MAXT][2];
static short priv_b[MAXT][5];

static void
body (void *p)
{
  (void) p;
  int tn = omp_get_thread_num ();
  int i, e;
  long istart, iend;
  g_nt = omp_get_num_threads ();

  for (e = 0; e < 12; e++) priv_x[tn][e] = 0;
  for (e = 0; e < 4; e++) priv_z[tn][e] = 0;
  for (e = 0; e < 3; e++) priv_y[tn][e] = 1;
  for (e = 0; e < 4; e++) priv_a[tn][e] = 0;
  for (e = 0; e < 2; e++) priv_w[tn][e] = ~0L;
  for (e = 0; e < 5; e++) priv_b[tn][e] = SHRT_MIN;

  if (GOMP_loop_static_start (0, 128, 1, 0, &istart, &iend))
    {
      do
	{
	  for (i = istart; i < iend; i++)
	    {
	      priv_x[tn][(i / 64) * 6 + (i % 3) * 2 + ((i / 4) & 1)] += i;
	      if ((i & 15) == 1)
		priv_y[tn][0] *= 3;
	      if ((i & 31) == 2)
		priv_y[tn][1] *= 7;
	      if ((i & 63) == 3)
		priv_y[tn][2] *= 17;
	      priv_z[tn][i / 32] += (i & 3);
	      if (i < 4)
		priv_z[tn][i] += i;
	      priv_a[tn][i / 32] |= 1ULL << (i & 30);
	      priv_w[tn][i & 1] &= ~(1L << (i / 17 * 3));
	      if ((i % 79) > priv_b[tn][0])
		priv_b[tn][0] = i % 79;
	      if ((i % 13) > priv_b[tn][1])
		priv_b[tn][1] = i % 13;
	      if ((i % 23) > priv_b[tn][2])
		priv_b[tn][2] = i % 23;
	      if ((i % 85) > priv_b[tn][3])
		priv_b[tn][3] = i % 85;
	      if ((i % 192) > priv_b[tn][4])
		priv_b[tn][4] = i % 192;
	    }
	}
      while (GOMP_loop_static_next (&istart, &iend));
    }
  GOMP_loop_end ();
}

__attribute__((noinline, noclone)) void
foo (int (*x)[3][2], int *y, long w[1][2], int p1, long p2, long p3, int p4,
     int p5, long p6, short p7)
{
  unsigned long long a[p7 + 4];
  short b[p7];
  int i, t, e;
  for (i = 0; i < p7 + 4; i++)
    {
      if (i < p7)
	b[i] = -6;
      a[i] = 0;
    }

  GOMP_parallel (body, 0, 0, 0);

  for (e = 0; e < 12; e++)
    {
      int s = ((int *) x)[e];
      for (t = 0; t < g_nt; t++) s += priv_x[t][e];
      ((int *) x)[e] = s;
    }
  for (e = 0; e < 4; e++)
    {
      int s = z[e];
      for (t = 0; t < g_nt; t++) s += priv_z[t][e];
      z[e] = (char) s;
    }
  for (e = 0; e < 3; e++)
    {
      int p = y[e];
      for (t = 0; t < g_nt; t++) p *= priv_y[t][e];
      y[e] = p;
    }
  for (e = 0; e < 4; e++)
    {
      unsigned long long o = a[e];
      for (t = 0; t < g_nt; t++) o |= priv_a[t][e];
      a[e] = o;
    }
  for (e = 0; e < 2; e++)
    {
      long an = w[0][e];
      for (t = 0; t < g_nt; t++) an &= priv_w[t][e];
      w[0][e] = an;
    }
  for (e = 0; e < 5; e++)
    {
      short m = b[e];
      for (t = 0; t < g_nt; t++)
	if (priv_b[t][e] > m) m = priv_b[t][e];
      b[e] = m;
    }

  for (i = 0; i < 9; i++)
    if (a[i] != (i < 4 ? 0x55555555ULL : 0))
      __builtin_abort ();
  if (b[0] != 78 || b[1] != 12 || b[2] != 22 || b[3] != 84 || b[4] != 127)
    __builtin_abort ();
}

int
main ()
{
  int a[4][3][2] = {};
  static int a2[4][3][2] = {{{ 0, 0 }, { 0, 0 }, { 0, 0 }},
			    {{ 312, 381 }, { 295, 356 }, { 337, 335 }},
			    {{ 1041, 975 }, { 1016, 1085 }, { 935, 1060 }},
			    {{ 0, 0 }, { 0, 0 }, { 0, 0 }}};
  int y[5] = { 0, 1, 1, 1, 0 };
  int y2[5] = { 0, 6561, 2401, 289, 0 };
  char z2[10] = { 48, 49, 50, 51, 0, 0, 0, 0, 0, 0 };
  long w[1][2] = { ~0L, ~0L };
  foo (&a[1], y + 1, w, 1, 3L, 4L, 3, 4, 2L, 5);
  if (__builtin_memcmp (a, a2, sizeof (a))
      || __builtin_memcmp (y, y2, sizeof (y))
      || __builtin_memcmp (z, z2, sizeof (z))
      || w[0][0] != ~0x249249L
      || w[0][1] != ~0x249249L)
    __builtin_abort ();
  return 0;
}
