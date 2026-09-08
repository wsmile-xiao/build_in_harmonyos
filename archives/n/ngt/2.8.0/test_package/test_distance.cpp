// test_distance — NGT distance-type matrix on float objects.
// Builds a separate small ANNG index per distance type (L1 / L2 / Angle /
// Cosine), persists it, reopens, and verifies by self-query that the exact
// stored object is the top-1 nearest neighbour with distance ~ 0.
// 4 distance types × (property readback 2 + 3 self-queries × 2) = 32 checks.
#include "test_common.h"

#include <cstdio>


static void runDistanceType(const char *name, const char *idxDir,
                            NGT::ObjectSpace::DistanceType dt, int n, int dim, unsigned seed) {
  auto data = genFloatData(n, dim, seed);
  SETCTX(name);
  try {
    NGT::Property prop;
    prop.dimension = dim;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = dt;
    NGT::Index::create(idxDir, prop);
    {
      NGT::Index index(idxDir);
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      index.save();
    }
    NGT::Index r(idxDir);
    NGT::Property got;
    r.getProperty(got);
    CHECK(static_cast<int>(got.dimension) == dim, "readback dimension");
    CHECK(static_cast<int>(got.distanceType) == static_cast<int>(dt),
          "readback distanceType");
    for (int q = 0; q < 3; ++q) runSelfQuery(r, data[q], q + 1, q);
  } catch (NGT::Exception &e) {
    ++g_checks;
    ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks;
    ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
}

int main() {
  runDistanceType("float-L1", "idx_distance_l1", NGT::ObjectSpace::DistanceType::DistanceTypeL1, 120, 8, 101);
  runDistanceType("float-L2", "idx_distance_l2", NGT::ObjectSpace::DistanceType::DistanceTypeL2, 120, 8, 102);
  runDistanceType("float-Angle", "idx_distance_angle", NGT::ObjectSpace::DistanceType::DistanceTypeAngle, 120, 8, 103);
  runDistanceType("float-Cosine", "idx_distance_cosine", NGT::ObjectSpace::DistanceType::DistanceTypeCosine, 120, 8, 104);
  return finishReport("test_distance");
}
