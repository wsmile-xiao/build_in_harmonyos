void
with_offset ()
{
  struct S {
     int *ptr1, *ptr2;
  };
  struct S s1, s2;
  int *a, *b, *c, *d;
  s1.ptr1 = (int *) 0L;
  s1.ptr2 = (int *) 0xdeedbeef;
  s2.ptr1 = (int *) 0L;
  s2.ptr2 = (int *) 0xdeedbeef;
  a = (int *) 0L;
  b = (int *) 0xdeedbeef;
  c = (int *) 0L;
  d = (int *) 0xdeedbeef;

  int n1, n2, n3, n4;
  n1 = n2 = n3 = n4 = 0;

  /* target enter data map(...): no-op (zero-length sections) */

  /* target map(...): host fallback, pointers unchanged */
  {
    if (s2.ptr1 != (void *) 0L || s2.ptr2 != (void *) 0xdeedbeef
	|| c != (void *) 0L || d != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  {
    if (s1.ptr1 != (void *) 0L || s1.ptr2 != (void *) 0xdeedbeef
	|| a != (void *) 0L || b != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  {
    if (s1.ptr1 != (void *) 0L || s1.ptr2 != (void *) 0xdeedbeef
	|| a != (void *) 0L || b != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  /* target exit data: no-op */
}

int
main ()
{
  struct S {
     int *ptr1, *ptr2;
  };
  struct S s1, s2;
  int *a, *b, *c, *d;
  s1.ptr1 = (int *) 0L;
  s1.ptr2 = (int *) 0xdeedbeef;
  s2.ptr1 = (int *) 0L;
  s2.ptr2 = (int *) 0xdeedbeef;
  a = (int *) 0L;
  b = (int *) 0xdeedbeef;
  c = (int *) 0L;
  d = (int *) 0xdeedbeef;

  int n1, n2, n3, n4;
  n1 = n2 = n3 = n4 = 0;

  /* target enter data map(...): no-op */

  {
    if (s2.ptr1 != (void *) 0L || s2.ptr2 != (void *) 0xdeedbeef
	|| c != (void *) 0L || d != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  {
    if (s1.ptr1 != (void *) 0L || s1.ptr2 != (void *) 0xdeedbeef
	|| a != (void *) 0L || b != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  {
    if (s1.ptr1 != (void *) 0L || s1.ptr2 != (void *) 0xdeedbeef
	|| a != (void *) 0L || b != (void *) 0xdeedbeef)
      __builtin_abort ();
  }

  /* target exit data: no-op */

  with_offset ();
}
