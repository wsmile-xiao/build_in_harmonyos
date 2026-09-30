int
main ()
{
  int i, n;
  int data[] = {1,2};
  struct S {
    int **ptrset;
    int **ptrset2;
  };

  struct S s1, *sptr1;
  s1.ptrset = (int **) __builtin_malloc (sizeof(void*) * 3);
  s1.ptrset2 = (int **) __builtin_malloc (sizeof(void*) * 3);
  s1.ptrset[0] = data;
  s1.ptrset[1] = data;
  s1.ptrset[2] = data;
  s1.ptrset2[0] = data;
  s1.ptrset2[1] = data;
  s1.ptrset2[2] = data;
  sptr1 = &s1;

  i = 1;
  n = 0;
  /* target enter data map(...): no-op x3 */

  /* target map(...): host fallback */
  if (sptr1->ptrset2[1][0] != 1 || sptr1->ptrset2[1][1] != 2)
    __builtin_abort ();

  /* target exit data map(...): no-op x3 */

  __builtin_free (s1.ptrset);
  __builtin_free (s1.ptrset2);
}
