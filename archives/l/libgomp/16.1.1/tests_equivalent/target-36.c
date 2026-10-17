int
main ()
{
  int ah, bh, n = 1024;
  /* target map(from:ah,bh) + simd lastprivate(b): host fallback, serial */
  {
    int a, b;
    for (a = 0; a < n; a++)
      {
	b = a + n + 1;
	asm volatile ("" : "+r"(b));
      }
    ah = a, bh = b;
  }
  if (ah != n || bh != 2 * n)
    __builtin_abort ();
}
