extern void abort (void);
struct S { int s; int *u; int v[5]; };
volatile int z;

int
main ()
{
  int u[10] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 }, err = 0;
  struct S s = { 9, u + 3, { 10, 11, 12, 13, 14 } };
  int *v = u + 4;
  /* target enter data / update: no-ops on host (data in place) */
  s.s++;
  u[3]++;
  s.v[1]++;
  /* target map(alloc:...) map(from:err) */
  {
    err = 0;
    if (s.s != 10 || s.v[1] != 12 || s.v[2] != 12 || s.v[3] != 13)
      err = 1;
    if (v[-1] != 4 || v[0] != 4 || v[1] != 5 || v[2] != 6 || v[3] != 7)
      err = 1;
    s.s++;
    s.v[2] += 2;
    v[-1] = 5;
    v[3] = 9;
  }
  if (err)
    abort ();
  /* target map(alloc:s.u[0:5]) */
  {
    err = 0;
    if (s.u[0] != 5 || s.u[1] != 4 || s.u[2] != 5 || s.u[3] != 6 || s.u[4] != 9)
      err = 1;
    s.u[1] = 12;
  }
  /* target update from: no-op */
  if (err || s.s != 11 || u[0] != 0 || u[1] != 1 || u[2] != 2 || u[3] != 5
      || u[4] != 12 || u[5] != 5 || u[6] != 6 || u[7] != 9 || u[8] != 8
      || u[9] != 9 || s.v[0] != 10 || s.v[1] != 12 || s.v[2] != 14
      || s.v[3] != 13 || s.v[4] != 14)
    abort ();
  /* target exit data: no-ops */
  return 0;
}
