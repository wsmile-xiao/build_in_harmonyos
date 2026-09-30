/* Testing 'has_device_addr' clause with variable sized array. */

int
foo (int size)
{
  int x[size];

  /* target data + use_device_addr + has_device_addr: host pointers unchanged */
  for (int i = 0; i < size; i++)
    x[i] = i;
  for (int i = 0; i < size; i++)
    if (x[i] != i)
      __builtin_abort ();

  for (int i = 0; i < size; i++)
    x[i] = i;
  for (int i = 0; i < size; i++)
    if (x[i] != i)
      __builtin_abort ();

  return 0;
}

int
main ()
{
  foo (40);

  return 0;
}
