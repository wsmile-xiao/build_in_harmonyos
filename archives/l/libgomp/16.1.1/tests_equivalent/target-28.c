extern void abort (void);

int g;

int
foo (void)
{
  static int s;
  return ++s + g;
}

int
bar (void)
{
  static int s;
  return ++s;
}

int
main ()
{
  int r;
  /* target map(from:r): host fallback */
  {
    r = (foo () == 1) + (bar () == 1);
    r += (foo () == 2) + (bar () == 2);
  }
  if (r != 4)
    abort ();
  return 0;
}
