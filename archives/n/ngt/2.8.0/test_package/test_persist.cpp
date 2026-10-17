// test_persist — NGT index persistence: save then re-open (read-write and
// read-only) must reproduce the same object count and keep exact nearest
// neighbour lookups working across every open session.
// 4 open sessions × (object count 1 + 2 self-queries × 2) = 20 checks.
#include "test_common.h"

#include <cstdio>

int main() {
  const char *name = "test_persist";
  SETCTX(name);
  const int dim = 12, n = 100;
  auto data = genFloatData(n, dim, 401);
  try {
    NGT::Property prop;
    prop.dimension = dim;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    NGT::Index::create("idx_persist", prop);
    {
      NGT::Index index("idx_persist");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      CHECK(index.getNumberOfObjects() == static_cast<size_t>(n), "object count after build");
      index.save();
    }
    // open #1: read-write reopen after save
    {
      NGT::Index r("idx_persist");
      CHECK(r.getNumberOfObjects() == static_cast<size_t>(n), "object count after reopen (rw)");
      runSelfQuery(r, data[0], 1, 0);
      runSelfQuery(r, data[1], 2, 1);
    }
    // open #2: read-only reopen
    {
      NGT::Index ro("idx_persist", true);
      CHECK(ro.getNumberOfObjects() == static_cast<size_t>(n), "object count after reopen (ro)");
      runSelfQuery(ro, data[2], 3, 2);
      runSelfQuery(ro, data[3], 4, 3);
    }
    // open #3: second read-write session
    {
      NGT::Index r2("idx_persist");
      CHECK(r2.getNumberOfObjects() == static_cast<size_t>(n), "object count after 2nd reopen (rw)");
      runSelfQuery(r2, data[4], 5, 4);
      runSelfQuery(r2, data[5], 6, 5);
    }
    // open #4: read-only again (search stability across repeated loads)
    {
      NGT::Index ro2("idx_persist", true);
      CHECK(ro2.getNumberOfObjects() == static_cast<size_t>(n), "object count after 3rd reopen (ro)");
      runSelfQuery(ro2, data[6], 7, 6);
      runSelfQuery(ro2, data[7], 8, 7);
    }
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
  return finishReport(name);
}
