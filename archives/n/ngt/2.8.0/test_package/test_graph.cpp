// test_graph — NGT graph-type coverage (ANNG default + ONNG + IANNG) for
// float/L2 objects.  Graph type is selected through the Property.graphType
// field before Index::create(); after save/reopen the stored graph type is
// read back and self-query verifies the constructed graph is searchable.
// 3 graph types × (graphType readback + dimension readback + 3 self-queries × 2) = 24 checks.
#include "test_common.h"

#include <cstdio>


static void runGraphType(const char *name, const char *idxDir,
                         NGT::NeighborhoodGraph::GraphType gt, int n, int dim, unsigned seed) {
  auto data = genFloatData(n, dim, seed);
  SETCTX(name);
  try {
    NGT::Property prop;
    prop.dimension = dim;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    prop.graphType = gt;
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
    CHECK(static_cast<int>(got.graphType) == static_cast<int>(gt), "readback graphType");
    CHECK(static_cast<int>(got.dimension) == dim, "readback dimension");
    for (int q = 0; q < 3; ++q) runSelfQuery(r, data[q], q + 1, q);
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
}

int main() {
  runGraphType("ANNG", "idx_graph_anng", NGT::NeighborhoodGraph::GraphType::GraphTypeANNG, 120, 8, 301);
  runGraphType("ONNG", "idx_graph_onng", NGT::NeighborhoodGraph::GraphType::GraphTypeONNG, 100, 8, 302);
  runGraphType("IANNG", "idx_graph_ianng", NGT::NeighborhoodGraph::GraphType::GraphTypeIANNG, 100, 8, 303);
  return finishReport("test_graph");
}
