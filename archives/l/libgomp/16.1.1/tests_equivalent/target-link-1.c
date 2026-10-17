struct S { int s, t; };

int a = 1, b = 1;
double c[27];
struct S d = { 8888, 8888 };

int
foo (void)
{
  return a++ + b++;
}

int
bar (int n)
{
  int *p1 = &a;
  int *p2 = &b;
  c[n] += 2.0;
  d.s -= 2;
  d.t -= 2;
  return *p1 + *p2 + d.s + d.t;
}

int
main ()
{
  a = b = 2;
  d.s = 17;
  d.t = 18;

  int res, n = 10;
  /* target map(to:a,b,c,d) map(from:res): host fallback */
  {
    res = foo () + foo ();
    c[n] = 3.0;
    res += bar (n);
  }

  int shared_mem = 0;
  /* target map(alloc:shared_mem): host fallback */
  shared_mem = 1;

  if ((shared_mem && res != (2 + 2) + (3 + 3) + (4 + 4 + 15 + 16))
      || (!shared_mem && res != (2 + 1) + (3 + 2) + (4 + 3 + 15 + 16)))
    __builtin_abort ();

  /* target enter data map(to:c) + target update from(c): no-op */
  res = (int) (c[n] + 0.5);
  if ((shared_mem && res != 5) || (!shared_mem && res != 0))
    __builtin_abort ();

  /* target map(to:a,b) map(from:res) */
  res = foo ();

  if ((shared_mem && res != 4 + 4) || (!shared_mem && res != 2 + 3))
    __builtin_abort ();

  return 0;
}
