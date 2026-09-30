int
main ()
{
  int i, n;
  int data[] = {1,2};
  struct S { int **ptrset; };

  struct S s1, *sptr1;
  s1.ptrset = (int **) __builtin_malloc (sizeof(void*) * 3);
  s1.ptrset[0] = data;
  s1.ptrset[1] = data;
  s1.ptrset[2] = data;
  sptr1 = &s1;

  i = 1;
  n = 0;
  /* target enter data map(...): no-op */
  /* target enter data map(...): no-op */

  /* target exit data map(...): no-op */
  /* target exit data map(...): no-op */

  __builtin_free (s1.ptrset);

  struct S s2, *sptr2;
  s2.ptrset = (int **) __builtin_malloc (sizeof(void*) * 3);
  s2.ptrset[0] = data;
  s2.ptrset[1] = data;
  s2.ptrset[2] = data;
  sptr2 = &s2;

  i = 1;
  n = 2;
  /* target enter data map(...): no-op */
  /* target enter data map(...): no-op */

  /* target: host fallback */
  if (sptr2->ptrset[1][0] != 1 || sptr2->ptrset[1][1] != 2)
    __builtin_abort ();

  /* target exit data map(...): no-op */
  /* target exit data map(...): no-op */

  __builtin_free (s2.ptrset);
}
