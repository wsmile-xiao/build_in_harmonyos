extern void abort (void);
struct S { int e, f; };

void
foo (int n)
{
  int a[4] = { 0, 1, 2, 3 }, b[n], c = 4;
  struct S d = { 5, 6 };
  int *p = a + 1, i, err;
  for (i = 0; i < n; i++)
    b[i] = 9 + i;
  /* target data use_device_ptr + target is_device_ptr: host pointers unchanged */
  {
    err = 0;
    for (i = 0; i < 4; i++)
      if (p[i - 1] != i)
	err = 1;
  }
  if (err)
    abort ();
  for (i = 0; i < 4; i++)
    a[i] = 23 + i;
  {
    err = 0;
    for (i = 0; i < 4; i++)
      if (a[i] != 23 + i)
	err = 1;
  }
  if (err)
    abort ();
  {
    err = 0;
    for (i = 0; i < 4; i++)
      if (b[i] != 9 + i)
	err = 1;
  }
  if (err)
    abort ();
  {
    int *q = &c;
    {
      err = *q != 4;
    }
  }
  if (err)
    abort ();
  {
    struct S *r = &d;
    {
      err = r->e != 5 || r->f != 6;
    }
  }
  if (err)
    abort ();
}

int
main ()
{
  foo (9);
  return 0;
}
