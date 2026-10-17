// test_batch — multiple queries against one index session ("batch query").
// Batch A drives the high-level NGT::SearchQuery interface (a
// SearchContainer); Batch B drives the lower-level object-space path: query
// objects are allocated through NGT::Index::allocateObject(), wrapped in a
// raw NGT::SearchContainer and searched with NGT::Index::search(), then
// released with deleteObject(). Both batches must return the exact stored
// object for every query.
// Batch A 8 queries × 2 + Batch B 4 queries × 2 = 24 checks.
#include "test_common.h"

#include <cstdio>

int main() {
  const char *name = "test_batch";
  SETCTX(name);
  const int dim = 10, n = 120;
  auto data = genFloatData(n, dim, 601);
  try {
    NGT::Property prop;
    prop.dimension = dim;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    NGT::Index::create("idx_batch", prop);
    {
      NGT::Index index("idx_batch");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      index.save();
    }
    NGT::Index r("idx_batch");
    // Batch A: 8 queries through SearchQuery
    for (int q = 0; q < 8; ++q) runSelfQuery(r, data[q], q + 1, q);
    // Batch B: 4 queries through allocated-object SearchContainer
    const int bIdx[4] = {20, 21, 22, 23};
    for (int i = 0; i < 4; ++i) {
      int qi = bIdx[i];
      NGT::Object *qo = r.allocateObject(data[qi]);
      NGT::SearchContainer sc(*qo);
      NGT::ObjectDistances objs;
      sc.setResults(&objs);
      sc.setSize(5);
      sc.setEpsilon(0.1);
      r.search(sc);
      char msg_id[160], msg_d[160];
      std::snprintf(msg_id, sizeof(msg_id), "sc-q%d: top-1 is the query itself (id=%d)", qi, qi + 1);
      std::snprintf(msg_d, sizeof(msg_d), "sc-q%d: top-1 distance ~ 0", qi);
      if (objs.empty()) {
        std::snprintf(msg_id, sizeof(msg_id), "sc-q%d: result set is empty", qi);
        CHECK(false, msg_id);
      } else {
        CHECK(static_cast<int>(objs[0].id) == qi + 1, msg_id);
        CHECK(std::fabs(objs[0].distance) < 1e-3, msg_d);
      }
      r.deleteObject(qo);
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
