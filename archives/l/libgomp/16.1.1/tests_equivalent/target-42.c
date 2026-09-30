#include <stdio.h>

int
on_nvptx (void)
{
  return 1;
}

int
on_gcn (void)
{
  return 2;
}

int
on (void)
{
  return 0;
}

int
main ()
{
  int v;
  /* target map(from:v): host fallback -> on() returns 0 */
  v = on ();
  switch (v)
    {
    default:
      printf ("Host fallback or unknown offloading\n");
      break;
    case 1:
      printf ("Offloading to NVidia PTX\n");
      break;
    case 2:
      printf ("Offloading to AMD GCN\n");
      break;
    }
  return 0;
}
