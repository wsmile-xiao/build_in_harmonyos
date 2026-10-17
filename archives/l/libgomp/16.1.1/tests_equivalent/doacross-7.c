/* Equiv-rewrite of upstream libgomp.c/doacross-7.c (ordered doacross,
 * schedule(guided), omp_cur_iteration sink).  doacross loops lowered to
 * equivalent serialization inside a serialized GOMP_parallel region
 * (dependency order trivially satisfied by program order). */
extern void abort (void);
extern void GOMP_parallel (void (*) (void *), void *, unsigned, unsigned);

#define N 256
int a[N], b[N / 16][8][4], c[N / 32][8][8], g[N / 16][8][6];
volatile int d, e;
volatile unsigned long long f;

static void
body (void *unused)
{
  (void) unused;
  unsigned long long i;
  int j, k, l, m;

  for (i = 1; i < N + f; i++)
    {
      a[i] = 1;
      if (i > 1)
	{
	  l = a[i - 1];
	  if (l < 2)
	    abort ();
	}
      a[i] = 2;
      if (i < N - 1)
	{
	  l = a[i + 1];
	  if (l == 3)
	    abort ();
	}
      a[i] = 3;
    }

  for (i = 3; i < N / 16 - 1 + f; i++)
    for (j = 0; j < 8; j += 2)
      for (k = 1; k <= 3; k++)
	{
	  b[i][j][k] = 1;
	  if (j >= 2 && k > 1)
	    {
	      l = b[i][j - 2][k - 1];
	      if (l < 2)
		abort ();
	    }
	  b[i][j][k] = 2;
	  if (i >= 5 && j >= 2 && k < 3)
	    {
	      l = b[i - 2][j - 2][k + 1];
	      if (l < 2)
		abort ();
	    }
	  if (i != 3 || j || k != 1)
	    {
	      if (k != 1)
		l = b[i][j][k - 1];
	      else if (j)
		l = b[i][j - 2][3];
	      else
		l = b[i - 1][6][3];
	      if (l < 2)
		abort ();
	    }
	  b[i][j][k] = 3;
	}

#define A(n) int n;
#define B(n) A(n##0) A(n##1) A(n##2) A(n##3)
#define C(n) B(n##0) B(n##1) B(n##2) B(n##3)
#define D(n) C(n##0) C(n##1) C(n##2) C(n##3)
  D(m)
#undef A

  for (i = 2; i < N / 32 + f; i++)
    for (j = 7; j > 1; j--)
      for (k = 6; k >= 0; k -= 2)
#define A(n) for (n = 4; n < 5; n++)
	D(m)
#undef A
	{
	  c[i][j][k] = 1;
	  if (i != 2 || j != 7 || k != 6)
	    {
	      if (k != 6)
		l = c[i][j][k + 2];
	      else if (j != 7)
		l = c[i][j + 1][0];
	      else
		l = c[i - 1][2][0];
	      if (l < 2)
		abort ();
	    }
	  c[i][j][k] = 2;
	  c[i][j][k] = 3;
	}

  for (j = 0; j < N / 16 - 1; j++)
    for (k = 0; k < 8; k += 2)
      for (i = 3; i <= 5 + f; i++)
	{
	  g[j][k][i] = 1;
	  if (k >= 2 && i > 3)
	    {
	      l = g[j][k - 2][i - 1];
	      if (l < 2)
		abort ();
	    }
	  g[j][k][i] = 2;
	  if (j || k || i != 3)
	    {
	      if (i != 3)
		l = g[j][k][i - 1];
	      else if (k)
		l = g[j][k - 2][5 + f];
	      else
		l = g[j - 1][6][5 + f];
	      if (l < 2)
		abort ();
	    }
	  if (j >= 3 && k < N / 16 - 3 && i == 5)
	    {
	      l = g[j - 3][k + 2][i - 2];
	      if (l < 2)
		abort ();
	    }
	  g[j][k][i] = 3;
	}

  for (i = 2; i < f + 3; i++)
    for (j = d + 1; j >= 0; j--)
      for (k = 0; k < d; k++)
	for (l = 0; l < d + 2; l++)
	  {
	    if (!e)
	      abort ();
	  }
  {
    if (i != 3 || j != -1 || k != 0)
      abort ();
    i = 8; j = 9; k = 10;
  }

  for (i = 2; i < f + 3; i++)
    for (j = d + 1; j >= 0; j--)
      for (k = 0; k < d + 2; k++)
	for (m = 0; m < d; m++)
	  {
	    abort ();
	  }
  if (i != 3 || j != -1 || k != 2 || m != 0)
    abort ();

  for (i = 2; i < f + 3; i++)
    for (j = d; j > 0; j--)
      for (k = 0; k < d + 2; k++)
	for (l = 0; l < d + 4; l++)
	  {
	    if (!e)
	      abort ();
	  }

  for (i = 0; i < N; i++)
    if (a[i] != 3 * (i >= 1))
      abort ();

  for (i = 0; i < N / 16; i++)
    for (j = 0; j < 8; j++)
      for (k = 0; k < 4; k++)
	if (b[i][j][k] != 3 * (i >= 3 && i < N / 16 - 1 && (j & 1) == 0 && k >= 1))
	  abort ();

  for (i = 0; i < N / 32; i++)
    for (j = 0; j < 8; j++)
      for (k = 0; k < 8; k++)
	if (c[i][j][k] != 3 * (i >= 2 && j >= 2 && (k & 1) == 0))
	  abort ();

  for (i = 0; i < N / 16; i++)
    for (j = 0; j < 8; j++)
      for (k = 0; k < 6; k++)
	if (g[i][j][k] != 3 * (i < N / 16 - 1 && (j & 1) == 0 && k >= 3))
	  abort ();
}

int
main (void)
{
  GOMP_parallel (body, 0, 1, 0);
  return 0;
}
