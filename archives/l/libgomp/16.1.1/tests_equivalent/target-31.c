/* Equiv-rewrite of upstream target-31.c.
 * #pragma omp target private/firstprivate/map + teams(num_teams,thread_limit)
 * + nested parallel(firstprivate/private) + atomic read/write/update + simd
 * manually lowered to GOMP ABI.  On host-only the target maps degenerate to
 * host pointers; target private/firstprivate become local copies; host teams
 * runs the 4 teams serially.
 */
#include <omp.h>
#include <stdlib.h>

extern void GOMP_teams_reg (void (*) (void *), void *, unsigned, unsigned, unsigned);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);
extern void GOMP_atomic_start (void);
extern void GOMP_atomic_end (void);
extern void GOMP_barrier (void);

int a = 1, b = 2, c = 3, d = 4;
int e[2] = { 5, 6 }, f[2] = { 7, 8 }, g[2] = { 9, 10 }, h[2] = { 11, 12 };

__attribute__((noinline)) void
use (int *k, int *l, int *m, int *n, int *o, int *p, int *q, int *r)
{
  asm volatile ("" : : "r" (k) : "memory");
  asm volatile ("" : : "r" (l) : "memory");
  asm volatile ("" : : "r" (m) : "memory");
  asm volatile ("" : : "r" (n) : "memory");
  asm volatile ("" : : "r" (o) : "memory");
  asm volatile ("" : : "r" (p) : "memory");
  asm volatile ("" : : "r" (q) : "memory");
  asm volatile ("" : : "r" (r) : "memory");
}

/* State shared across teams (target-level private/firstprivate + host maps). */
struct S {
  int a;			/* target private a */
  int e[2];			/* target private e */
  int c;			/* target firstprivate c */
  int g[2];			/* target firstprivate g */
  int *err, *r, *j, *l, *k, *m;	/* main locals (mapped) */
  long *s;
  int *t;
};

static void
par1 (struct S *S, int *b, int *d, int (*f)[2], int (*h)[2], int *k, int (*m)[2])
{
  int v1, v2, v3;
  GOMP_atomic_start (); v1 = S->c; GOMP_atomic_end ();
  GOMP_atomic_start (); v2 = S->g[0]; GOMP_atomic_end ();
  GOMP_atomic_start (); v3 = S->g[1]; GOMP_atomic_end ();
  if (v1 < 3 || v1 > 6
      || *d != 4
      || v2 < 9 || v2 > 15 || (v2 & 1) == 0
      || v3 < 10 || v3 > 19 || ((v3 - 10) % 3) != 0
      || (*h)[0] != 11 || (*h)[1] != 12 || *k != 14
      || (*m)[0] != 17 || (*m)[1] != 18)
    { GOMP_atomic_start (); *S->err = 1; GOMP_atomic_end (); }
  *b = omp_get_team_num ();
  if (*b >= 4)
    { GOMP_atomic_start (); *S->err = 1; GOMP_atomic_end (); }
  if (*b == 0)
    {
      S->a = omp_get_num_teams ();
      S->e[0] = 2 * S->a;
      S->e[1] = 3 * S->a;
    }
  (*f)[0] = 2 * (*b);
  (*f)[1] = 3 * (*b);
  GOMP_atomic_start (); S->c++; GOMP_atomic_end ();
  GOMP_atomic_start (); S->g[0] += 2; GOMP_atomic_end ();
  GOMP_atomic_start (); S->g[1] += 3; GOMP_atomic_end ();
  (*d)++;
  (*h)[0] += 2;
  (*h)[1] += 3;
  *k += *b;
  (*m)[0] += 2 * (*b);
  (*m)[1] += 3 * (*b);
}

struct P2 {
  struct S *S;
  int *b;
  int (*h)[2];
  int *k;
  int (*m)[2];
  int u1;			/* firstprivate original value */
  int u2[2];
  int *u3;			/* shared u3 array */
};

static void
par2_body (void *p)
{
  struct P2 *P = p;
  int u1 = P->u1;		/* firstprivate */
  int u2[2] = { P->u2[0], P->u2[1] };
  int i;			/* private */
  int w = omp_get_thread_num ();
  int x = 19;
  int y[2] = { 20, 21 };
  int v = 24;
  int ll[64];
  if (u1 != 14 || u2[0] != 17 || u2[1] != 18)
    { GOMP_atomic_start (); *P->S->err = 1; GOMP_atomic_end (); }
  u1 += w;
  u2[0] += 2 * w;
  u2[1] += 3 * w;
  use (&u1, u2, &P->S->t[*P->b], P->S->l, P->k, *P->m, P->S->j, *P->h);
  if (omp_get_thread_num () == 0)	/* master */
    P->S->t[*P->b] = omp_get_num_threads ();
  GOMP_atomic_start (); (*P->S->j)++; GOMP_atomic_end ();
  GOMP_atomic_start (); P->S->l[0] += 2; GOMP_atomic_end ();
  GOMP_atomic_start (); P->S->l[1] += 3; GOMP_atomic_end ();
  GOMP_atomic_start (); *P->k += 4; GOMP_atomic_end ();
  GOMP_atomic_start (); (*P->m)[0] += 5; GOMP_atomic_end ();
  GOMP_atomic_start (); (*P->m)[1] += 6; GOMP_atomic_end ();
  x += w;
  y[0] += 2 * w;
  y[1] += 3 * w;
  /* #pragma omp simd safelen(32) private(v) */
  for (i = 0; i < 64; i++)
    {
      int vv = 3 * i;
      ll[i] = u1 + vv * u2[0] + u2[1] + x + y[0] + y[1] + vv + (*P->h)[0] + P->u3[i];
    }
  GOMP_barrier ();
  use (&u1, u2, &P->S->t[*P->b], P->S->l, P->k, *P->m, &x, y);
  if (w < 0 || w > 8 || w != omp_get_thread_num () || u1 != 14 + w
      || u2[0] != 17 + 2 * w || u2[1] != 18 + 3 * w
      || x != 19 + w || y[0] != 20 + 2 * w || y[1] != 21 + 3 * w
      || v != 24)
    { GOMP_atomic_start (); *P->S->err = 1; GOMP_atomic_end (); }
  for (i = 0; i < 64; i++)
    if (ll[i] != u1 + 3 * i * u2[0] + u2[1] + x + y[0] + y[1] + 3 * i + 13 + 14 + i)
      { GOMP_atomic_start (); *P->S->err = 1; GOMP_atomic_end (); }
}

struct P3 {
  struct S *S;
  int *b, *d;
  int (*f)[2], (*h)[2];
  int *k, (*m)[2];
};

static void
par3_body (void *p)
{
  struct P3 *P = p;
  if (*P->b == 0)
    {
      *P->S->r = P->S->a;
      if (P->S->a != omp_get_num_teams ()
	  || P->S->e[0] != 2 * P->S->a
	  || P->S->e[1] != 3 * P->S->a)
	{ GOMP_atomic_start (); *P->S->err = 1; GOMP_atomic_end (); }
    }
  int v1, v2, v3;
  GOMP_atomic_start (); v1 = P->S->c; GOMP_atomic_end ();
  GOMP_atomic_start (); v2 = P->S->g[0]; GOMP_atomic_end ();
  GOMP_atomic_start (); v3 = P->S->g[1]; GOMP_atomic_end ();
  P->S->s[*P->b] = (long) v1 * 65536L + v2 * 256L + v3;
  if (*P->d != 5 || (*P->h)[0] != 13 || (*P->h)[1] != 15
      || *P->k != 14 + *P->b + 4 * P->S->t[*P->b]
      || (*P->m)[0] != 17 + 2 * *P->b + 5 * P->S->t[*P->b]
      || (*P->m)[1] != 18 + 3 * *P->b + 6 * P->S->t[*P->b]
      || *P->b != omp_get_team_num ()
      || (*P->f)[0] != 2 * *P->b || (*P->f)[1] != 3 * *P->b)
    { GOMP_atomic_start (); *P->S->err = 1; GOMP_atomic_end (); }
}

static void
teams_body (void *p)
{
  struct S *S = p;
  /* teams private(b,f) firstprivate(d,h,k,m) */
  int b, d, f[2], h[2], k, m[2];
  d = 4;			/* firstprivate d */
  h[0] = 11; h[1] = 12;		/* firstprivate h */
  k = *S->k;			/* firstprivate k = 14 */
  m[0] = S->m[0]; m[1] = S->m[1]; /* firstprivate m */
  /* b, f private (uninitialized; assigned in par1) */

  int u1 = k, u2[2] = { m[0], m[1] };
  int u3[64];
  int i;
  for (i = 0; i < 64; i++)
    u3[i] = k + i;

  /* first parallel num_threads(1): equivalent to a direct (single-thread) call */
  par1 (S, &b, &d, &f, &h, &k, &m);

  use (&S->a, &b, &S->c, &d, S->e, f, S->g, h);

  struct P2 P2;
  P2.S = S; P2.b = &b; P2.h = &h; P2.k = &k; P2.m = &m;
  P2.u1 = u1; P2.u2[0] = u2[0]; P2.u2[1] = u2[1];
  P2.u3 = u3;
  GOMP_parallel (par2_body, &P2, 0, 0);

  struct P3 P3;
  P3.S = S; P3.b = &b; P3.d = &d; P3.f = &f; P3.h = &h; P3.k = &k; P3.m = &m;
  GOMP_parallel (par3_body, &P3, 1, 0);
}

int
main (void)
{
  int err = 0, r = -1, t[4];
  long s[4] = { -1, -2, -3, -4 };
  int j = 13, k = 14, l[2] = { 15, 16 }, m[2] = { 17, 18 };

  struct S S;
  S.err = &err; S.r = &r; S.j = &j; S.l = l; S.k = &k; S.m = m; S.s = s; S.t = t;
  S.a = 0;			/* target private a (assigned before use) */
  S.e[0] = 0; S.e[1] = 0;	/* target private e (assigned before use) */
  S.c = c;			/* target firstprivate c = 3 */
  S.g[0] = g[0]; S.g[1] = g[1]; /* target firstprivate g = {9,10} */

  GOMP_teams_reg (teams_body, &S, 4, 8, 0);

  if (err != 0) abort ();
  if (r < 1 || r > 4) abort ();
  if (a != 1 || b != 2 || c != 3 || d != 4) abort ();
  if (e[0] != 5 || e[1] != 6 || f[0] != 7 || f[1] != 8) abort ();
  if (g[0] != 9 || g[1] != 10 || h[0] != 11 || h[1] != 12) abort ();
  int i, cnt = 0;
  for (i = 0; i < r; i++)
    if ((s[i] >> 16) < 3 + 1 || (s[i] >> 16) > 3 + 4
	|| ((s[i] >> 8) & 0xff) < 9 + 2 * 1 || ((s[i] >> 8) & 0xff) > 9 + 2 * 4
	|| (s[i] & 0xff) < 10 + 3 * 1 || (s[i] & 0xff) > 10 + 3 * 4
	|| t[i] < 1 || t[i] > 8)
      abort ();
    else
      cnt += t[i];
  if (j != 13 + cnt || l[0] != 15 + 2 * cnt || l[1] != 16 + 3 * cnt) abort ();
  return 0;
}
