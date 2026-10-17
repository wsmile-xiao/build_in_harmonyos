__attribute__ ((__noinline__)) int addit (int a, int b)
{
  return a + b;
}

__attribute__ ((__noinline__))
void callit (int *a, int *b, int *c)
{
  int i;
  /* #pragma omp for simd -> serial loop (vectorization hint) */
  for (i = 0; i < 16; i++)
    c[i] = addit (a[i], b[i]);
}

int main (void)
{
  int aa[16], bb[16], cc[16];
  int i;
  for (i = 0; i < 16; i++)
    {
      aa[i] = i;
      bb[i] = -i;
    }
  callit (aa, bb, cc);
  for (i = 0; i < 16; i++)
    if (cc[i] != 0)
      return 1;
  return 0;
}
