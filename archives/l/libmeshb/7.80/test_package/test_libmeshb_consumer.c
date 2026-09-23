/* Consumer test for libMeshb 7.80.
 * Writes a small Meshb.7 mesh (2 vertices + 1 edge), reopens it and asserts
 * the stored version/dimension/keyword counts and values. */

#include <stdio.h>
#include <string.h>

#include "libmeshb7.h"

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

int main(void)
{
   const char* path = "consumer_test.meshb";

   /* write phase */
   long long w = GmfOpenMesh(path, GmfWrite, 2, 3);
   CHECK(w != 0);
   if (w)
   {
      GmfSetKwd(w, GmfVertices, 2);
      GmfSetLin(w, GmfVertices, 0.0, 0.0, 0.0, 0);
      GmfSetLin(w, GmfVertices, 1.0, 0.0, 0.0, 1);
      GmfSetKwd(w, GmfEdges, 1);
      GmfSetLin(w, GmfEdges, 1, 2, 0);
      GmfCloseMesh(w);
   }

   /* read-back phase */
   int ver = 0, dim = 0;
   long long r = GmfOpenMesh(path, GmfRead, &ver, &dim);
   CHECK(r != 0);
   if (r)
   {
      CHECK(ver == 2);
      CHECK(dim == 3);

      int nmb_ver = GmfStatKwd(r, GmfVertices);
      CHECK(nmb_ver == 2);
      int nmb_edg = GmfStatKwd(r, GmfEdges);
      CHECK(nmb_edg == 1);

      double x = -1.0, y = -1.0, z = -1.0;
      int ref = -1;

      GmfGotoKwd(r, GmfVertices);
      GmfGetLin(r, GmfVertices, &x, &y, &z, &ref);
      CHECK(x == 0.0 && y == 0.0 && z == 0.0 && ref == 0);
      GmfGetLin(r, GmfVertices, &x, &y, &z, &ref);
      CHECK(x == 1.0 && ref == 1);

      int v1 = 0, v2 = 0, eref = -1;
      GmfGotoKwd(r, GmfEdges);
      GmfGetLin(r, GmfEdges, &v1, &v2, &eref);
      CHECK(v1 == 1 && v2 == 2 && eref == 0);

      GmfCloseMesh(r);
   }

   remove(path);

   if (g_fails == 0)
   {
      printf("libmeshb consumer test: %d/%d checks passed\n", g_checks, g_checks);
      return 0;
   }
   fprintf(stderr, "libmeshb consumer test: %d/%d check(s) failed\n", g_fails, g_checks);
   return 1;
}
