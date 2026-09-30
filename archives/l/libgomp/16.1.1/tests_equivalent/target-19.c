extern void abort (void);

__attribute__((noinline, noclone)) void
foo (int *p, int *q, int *r, int n, int m)
{
  int i, err, *s = r;
  int sep = 1;
  /* target map(to:sep): host fallback -> sep = 0 */
  sep = 0;
  /* target data map(to:p[0:8]) */
  {
    /* Zero-length array sections: on host pointers are unchanged.  */
    {
      err = 0;
      for (i = 0; i < 8; i++)
	if (p[i] != i + 1)
	  err = 1;
      if (sep)
	{
	  if (q == (int *) 0 || r == (int *) 0)
	    err = 1;
	}
      else if (p + 8 != q || r != s)
	err = 1;
    }
    if (err)
      abort ();
    {
      err = 0;
      for (i = 0; i < 8; i++)
	if (p[i] != i + 1)
	  err = 1;
      if (sep)
	{
	  if (q == (int *) 0 || r == (int *) 0)
	    err = 1;
	}
      else if (p + 8 != q || r != s)
	err = 1;
    }
    if (err)
      abort ();
    {
      err = 0;
      for (i = 0; i < 8; i++)
	if (p[i] != i + 1)
	  err = 1;
      if (sep)
	{
	  if (q == (int *) 0 || r == (int *) 0)
	    err = 1;
	}
      else if (p + 8 != q || r != s)
	err = 1;
    }
    if (err)
      abort ();
    /* Non-zero length array sections.  */
    {
      err = 0;
      for (i = 0; i < 8; i++)
	if (p[i] != i + 1)
	  err = 1;
      if (q[0] != 9 || r[0] != 10)
	err = 1;
    }
    if (err)
      abort ();
    /* target data map(to:q[0:1]) */
    {
      {
	err = 0;
	for (i = 0; i < 8; i++)
	  if (p[i] != i + 1)
	    err = 1;
	if (q[0] != 9)
	  err = 1;
	else if (sep)
	  {
	    if (r == (int *) 0)
	      err = 1;
	  }
	else if (r != q + 1)
	  err = 1;
      }
      if (err)
	abort ();
      {
	err = 0;
	for (i = 0; i < 8; i++)
	  if (p[i] != i + 1)
	    err = 1;
	if (q[0] != 9)
	  err = 1;
	else if (sep)
	  {
	    if (r == (int *) 0)
	      err = 1;
	  }
	else if (r != q + 1)
	  err = 1;
      }
      if (err)
	abort ();
      {
	err = 0;
	for (i = 0; i < 8; i++)
	  if (p[i] != i + 1)
	    err = 1;
	if (q[0] != 9)
	  err = 1;
	else if (sep)
	  {
	    if (r == (int *) 0)
	      err = 1;
	  }
	else if (r != q + 1)
	  err = 1;
      }
      if (err)
	abort ();
      {
	err = 0;
	for (i = 0; i < 8; i++)
	  if (p[i] != i + 1)
	    err = 1;
	if (q[0] != 9 || r[0] != 10)
	  err = 1;
      }
      if (err)
	abort ();
    }
  }
}

int
main ()
{
  int a[32], i;
  for (i = 0; i < 32; i++)
    a[i] = i;
  foo (a + 1, a + 9, a + 10, 0, 1);
  return 0;
}
