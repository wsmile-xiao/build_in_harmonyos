/*
   Sample code used by the d-shlibs consumer test to build a minimal shared
   library (mirrors the fixture of upstream debian/tests/uppercase.d, which is
   the upstream autopkgtest that drives d-shlibmove).
 */
int test(int a)
{
  return a;
}
