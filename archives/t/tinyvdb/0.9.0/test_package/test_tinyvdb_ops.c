/* Consumer test for the packaged tinyvdb library.
 *
 * Exercises the real tinyvdb_mesh_ops / tinyvdb dense-grid API the same way
 * upstream's own tests/test_ops.c does: build a sphere SDF, measure it,
 * morph it, and assert the physical quantities move in the right direction.
 * Returns non-zero on failure.
 */

#include "tinyvdb_ops.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failures = 0;

#define EXPECT(cond) do { \
  if (!(cond)) { \
    fprintf(stderr, "FAIL [%s:%d]: %s\n", __FILE__, __LINE__, #cond); \
    ++g_failures; \
  } \
} while (0)

#define EXPECT_NEAR(a, b, tol) do { \
  double _a = (double)(a), _b = (double)(b); \
  if (fabs(_a - _b) > (double)(tol)) { \
    fprintf(stderr, "FAIL [%s:%d]: %s (= %g) ~= %s (= %g) within %g\n", \
            __FILE__, __LINE__, #a, _a, #b, _b, (double)(tol)); \
    ++g_failures; \
  } \
} while (0)

/* Build a sphere SDF on a 16^3 dense grid (same shape as upstream test_ops.c). */
static void make_sphere_sdf(tvdb_dense_grid* g, int n, float voxel_size, float radius_w) {
  tvdb_dense_grid_init(g, n, n, n);
  g->voxel_size = voxel_size;
  g->ox = g->oy = g->oz = -0.5f * (float)n * voxel_size;
  float cx = 0.0f, cy = 0.0f, cz = 0.0f;
  for (int iz = 0; iz < n; ++iz) {
    for (int iy = 0; iy < n; ++iy) {
      for (int ix = 0; ix < n; ++ix) {
        float wx = g->ox + ((float)ix + 0.5f) * voxel_size;
        float wy = g->oy + ((float)iy + 0.5f) * voxel_size;
        float wz = g->oz + ((float)iz + 0.5f) * voxel_size;
        float dx = wx - cx, dy = wy - cy, dz = wz - cz;
        g->data[(size_t)((iz * n + iy) * n + ix)] = sqrtf(dx*dx + dy*dy + dz*dz) - radius_w;
      }
    }
  }
}

int main(void) {
  /* 1. Volume of a unit-diameter sphere ~ (4/3)*pi*r^3 ~= 0.5236 */
  tvdb_dense_grid g;
  make_sphere_sdf(&g, 16, 0.1f, 0.5f);
  float vol = tvdb_volume(&g);
  EXPECT_NEAR(vol, 0.5236f, 0.05f);

  /* 2. Surface area ~ 4*pi*r^2 ~= 3.1416; coarse-grid zero-crossing estimator
   *    yields a loose bound on low resolutions. */
  float sa = tvdb_surface_area(&g);
  EXPECT(sa > 2.5f && sa < 8.0f);

  /* 3. Dilation must grow the enclosed volume; erosion must shrink it. */
  tvdb_dense_grid g2;
  tvdb_dense_grid_init(&g2, 16, 16, 16);
  g2.voxel_size = g.voxel_size;
  g2.ox = g.ox; g2.oy = g.oy; g2.oz = g.oz;
  memcpy(g2.data, g.data, (size_t)16 * 16 * 16 * sizeof(float));
  tvdb_dilate(&g2, 1);
  EXPECT(tvdb_volume(&g2) > vol);

  memcpy(g2.data, g.data, (size_t)16 * 16 * 16 * sizeof(float));
  tvdb_erode(&g2, 1);
  EXPECT(tvdb_volume(&g2) < vol);

  /* 4. CSG union of two co-centered spheres (r=0.5 and r=0.3) is the
   *    larger sphere: volume unchanged, still >= each operand. */
  tvdb_dense_grid g3;
  make_sphere_sdf(&g3, 16, 0.1f, 0.3f);
  float vol3 = tvdb_volume(&g3);
  tvdb_dense_grid uni;
  tvdb_dense_grid_init(&uni, 16, 16, 16);
  uni.voxel_size = g.voxel_size;
  uni.ox = g.ox; uni.oy = g.oy; uni.oz = g.oz;
  tvdb_csg_union(&g, &g3, &uni);
  float volu = tvdb_volume(&uni);
  EXPECT_NEAR(volu, vol, 0.05f);
  EXPECT(volu >= vol && volu >= vol3);

  tvdb_dense_grid_free(&g);
  tvdb_dense_grid_free(&g2);
  tvdb_dense_grid_free(&g3);
  tvdb_dense_grid_free(&uni);

  if (g_failures) {
    fprintf(stderr, "tinyvdb consumer test: %d FAILURES\n", g_failures);
    return 1;
  }
  printf("tinyvdb consumer test OK: dense-grid ops (volume/surface-area/"
         "dilate/erode/csg-union) verified through the packaged library\n");
  return 0;
}
