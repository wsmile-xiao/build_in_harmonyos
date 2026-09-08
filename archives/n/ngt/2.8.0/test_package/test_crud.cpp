// test_crud — NGT object deletion (remove) on a live index:
//   * build 100-object float/L2 ANNG index and confirm exact self match;
//   * remove ids 50 and 20 (descending so earlier ids stay stable), save,
//     reopen → object count decreases by exactly 2;
//   * the removed vectors are no longer returned at distance ~ 0;
//   * retained vectors still return their exact self match.
// Then a second removal (id 90) verifies incremental CRUD on the reopened
// index.
// Total checks = 15.
#include "test_common.h"

#include <cstdio>

// query an index for a vector that used to be stored; a successful removal
// means the exact vector is gone, so top-1 distance must NOT be ~ 0.
static void queryRemoved(NGT::Index &index, const std::vector<float> &vec, int removedId, int qIdx) {
  NGT::SearchQuery sq(vec);
  NGT::ObjectDistances objs;
  sq.setResults(&objs);
  sq.setSize(5);
  sq.setEpsilon(0.1);
  index.search(sq);
  char msg[160];
  if (objs.empty()) {
    std::snprintf(msg, sizeof(msg), "removed-q%d: result set empty", qIdx);
    CHECK(false, msg);
    return;
  }
  std::snprintf(msg, sizeof(msg), "removed-q%d: id %d no longer at distance ~0 (top1 id=%d dist=%.4f)",
                qIdx, removedId, static_cast<int>(objs[0].id), static_cast<double>(objs[0].distance));
  CHECK(std::fabs(objs[0].distance) > 1e-3, msg);
}

// retained-vector query: top-1 must be an exact match (distance ~ 0) without
// hard-coding the (shifted) object id.
static void queryRetained(NGT::Index &index, const std::vector<float> &vec, int qIdx) {
  NGT::SearchQuery sq(vec);
  NGT::ObjectDistances objs;
  sq.setResults(&objs);
  sq.setSize(5);
  sq.setEpsilon(0.1);
  index.search(sq);
  char msg[160];
  if (objs.empty()) {
    std::snprintf(msg, sizeof(msg), "retained-q%d: result set empty", qIdx);
    CHECK(false, msg);
    return;
  }
  std::snprintf(msg, sizeof(msg), "retained-q%d: exact self match found (id=%d dist=%.5f)", qIdx,
                static_cast<int>(objs[0].id), static_cast<double>(objs[0].distance));
  CHECK(std::fabs(objs[0].distance) < 1e-3, msg);
  CHECK(static_cast<int>(objs[0].id) > 0, "retained result id is valid");
}

int main() {
  const char *name = "test_crud";
  SETCTX(name);
  const int dim = 12, n = 100;
  auto data = genFloatData(n, dim, 501);
  try {
    NGT::Property prop;
    prop.dimension = dim;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    NGT::Index::create("idx_crud", prop);
    {
      NGT::Index index("idx_crud");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      CHECK(index.getNumberOfObjects() == static_cast<size_t>(n), "object count after build");
      index.save();
    }
    // sanity: ids 1 and 50 are exact self matches before removal
    {
      NGT::Index r("idx_crud");
      runSelfQuery(r, data[0], 1, 0);
      runSelfQuery(r, data[49], 50, 1);
    }
    // remove id 50 then id 20 (descending), persist and reopen
    {
      NGT::Index rw("idx_crud");
      rw.remove(50);
      rw.remove(20);
      rw.save();
    }
    NGT::Index r2("idx_crud");
    CHECK(r2.getNumberOfObjects() == static_cast<size_t>(n - 2), "object count after 2 removals");
    queryRemoved(r2, data[49], 50, 0);  // former id 50
    queryRemoved(r2, data[19], 20, 1);  // former id 20
    runSelfQuery(r2, data[0], 1, 2);    // id 1 unaffected by removals
    queryRetained(r2, data[30], 3);     // retained vector still exact-matchable
    // incremental second removal on the reopened index
    {
      NGT::Index rw2("idx_crud");
      rw2.remove(90);
      rw2.save();
    }
    NGT::Index r3("idx_crud");
    CHECK(r3.getNumberOfObjects() == static_cast<size_t>(n - 3), "object count after 3 removals");
    runSelfQuery(r3, data[0], 1, 4);
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
  return finishReport(name);
}
