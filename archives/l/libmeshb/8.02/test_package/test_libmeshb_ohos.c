/* HarmonyOS-specific test for libMeshb 8.02.
 * Writes the SAME 3-vertex + 1-triangle mesh in BOTH the ASCII (.mesh)
 * and binary (.meshb) formats, reopens each and asserts the stored
 * version/dimension/keyword counts and values.  Exercises only the public
 * API from the installed header libmeshb8.h. */

#include <stdio.h>
#include <string.h>

#include "libmeshb8.h"

static int g_checks = 0;
static int g_fails = 0;

static void check(int ok, const char* what, int line) {
    ++g_checks;
    if (!ok) {
        fprintf(stderr, "FAIL(line %d): %s\n", line, what);
        ++g_fails;
    }
}

#define CHECK(expr) check((expr), #expr, __LINE__)

/* Write a 3-vertex + 1-triangle mesh to path (format chosen by extension). */
static long long write_mesh(const char* path)
{
   long long w = GmfOpenMesh(path, GmfWrite, 2, 3);
   if (!w)
      return 0;
   GmfSetKwd(w, GmfVertices, 3);
   GmfSetLin(w, GmfVertices, 0.0, 0.0, 0.0, 1);
   GmfSetLin(w, GmfVertices, 1.0, 0.0, 0.0, 2);
   GmfSetLin(w, GmfVertices, 0.0, 1.0, 0.0, 3);
   GmfSetKwd(w, GmfTriangles, 1);
   GmfSetLin(w, GmfTriangles, 1, 2, 3, 0);
   GmfCloseMesh(w);
   return w;
}

static int read_back(const char* path)
{
   int ver = 0, dim = 0;
   long long r = GmfOpenMesh(path, GmfRead, &ver, &dim);
   CHECK(r != 0);
   if (!r)
      return 0;
   CHECK(ver == 2);
   CHECK(dim == 3);

   CHECK(GmfStatKwd(r, GmfVertices) == 3);
   CHECK(GmfStatKwd(r, GmfTriangles) == 1);

   double x = -1.0, y = -1.0, z = -1.0;
   int ref = -1;

   GmfGotoKwd(r, GmfVertices);
   GmfGetLin(r, GmfVertices, &x, &y, &z, &ref);
   CHECK(x == 0.0 && y == 0.0 && z == 0.0 && ref == 1);
   GmfGetLin(r, GmfVertices, &x, &y, &z, &ref);
   CHECK(x == 1.0 && y == 0.0 && z == 0.0 && ref == 2);
   GmfGetLin(r, GmfVertices, &x, &y, &z, &ref);
   CHECK(x == 0.0 && y == 1.0 && z == 0.0 && ref == 3);

   int t1 = 0, t2 = 0, t3 = 0, tref = -1;
   GmfGotoKwd(r, GmfTriangles);
   GmfGetLin(r, GmfTriangles, &t1, &t2, &t3, &tref);
   CHECK(t1 == 1 && t2 == 2 && t3 == 3 && tref == 0);

   GmfCloseMesh(r);
   return 1;
}

int main(void)
{
   const char* ascii_path = "ohos_test.mesh";
   const char* bin_path   = "ohos_test.meshb";

   /* ASCII roundtrip */
   CHECK(write_mesh(ascii_path) != 0);
   CHECK(read_back(ascii_path) != 0);

   /* Binary roundtrip */
   CHECK(write_mesh(bin_path) != 0);
   CHECK(read_back(bin_path) != 0);

   remove(ascii_path);
   remove(bin_path);

   if (g_fails == 0)
   {
      printf("libmeshb ohos test: %d/%d checks passed (ASCII + binary roundtrip)\n",
             g_checks, g_checks);
      return 0;
   }
   fprintf(stderr, "libmeshb ohos test: %d/%d check(s) failed\n", g_fails, g_checks);
   return 1;
}
