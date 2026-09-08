// test_package consumer test for NGT on HarmonyOS PC.
// Builds a small ANNG index from in-memory synthetic data, searches it, and
// verifies the nearest neighbour of each query equals the query itself
// (L2 distance ~ 0). Exercises the real NGT C++ API (NGT::Index) rather than
// being an empty-shell test.
#include <NGT/Index.h>

#include <cmath>
#include <cstdio>
#include <random>
#include <string>
#include <vector>

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "FAIL: %s\n", msg);                               \
      ++failures;                                                            \
    }                                                                        \
  } while (0)

int main() {
  const int dim = 16;
  const int n = 200;
  const std::string indexPath = "ngt_test_index";

  // Deterministic synthetic data (uniform in [0,10)^dim).
  std::mt19937 rng(12345);
  std::uniform_real_distribution<float> dist(0.0f, 10.0f);
  std::vector<std::vector<float>> data(n, std::vector<float>(dim));
  for (int i = 0; i < n; ++i)
    for (int d = 0; d < dim; ++d)
      data[i][d] = dist(rng);

  // ---- Index construction ------------------------------------------------
  try {
    NGT::Property property;
    property.dimension = dim;
    property.objectType = NGT::ObjectSpace::ObjectType::Float;
    property.distanceType = NGT::Index::Property::DistanceType::DistanceTypeL2;
    NGT::Index::create(indexPath, property);

    NGT::Index index(indexPath);
    for (int i = 0; i < n; ++i) {
      index.append(data[i]);
    }
    index.createIndex(16);
    index.save();
  } catch (NGT::Exception &e) {
    std::fprintf(stderr, "FAIL: index construction error: %s\n", e.what());
    return 1;
  } catch (const std::exception &e) {
    std::fprintf(stderr, "FAIL: index construction std error: %s\n", e.what());
    return 1;
  }

  // ---- Nearest neighbour search ------------------------------------------
  try {
    NGT::Index index(indexPath);
    NGT::Property property;
    index.getProperty(property);
    CHECK(static_cast<int>(property.dimension) == dim,
          "property.dimension == 16 after reopen");

    for (int q = 0; q < 5; ++q) {
      NGT::SearchQuery sq(data[q]);
      NGT::ObjectDistances objs;
      sq.setResults(&objs);
      sq.setSize(5);
      sq.setEpsilon(0.1);
      index.search(sq);

      if (objs.empty()) {
        std::fprintf(stderr, "FAIL: empty results for query %d\n", q);
        ++failures;
        continue;
      }
      // NGT object ids are 1-based; data[q] was appended as object id q+1.
      char msg_id[128], msg_d[128];
      std::snprintf(msg_id, sizeof(msg_id), "query %d: top-1 is itself (id=%d)",
                    q, static_cast<int>(objs[0].id));
      std::snprintf(msg_d, sizeof(msg_d),
                    "query %d: top-1 distance ~0 (got %.6f)", q,
                    static_cast<double>(objs[0].distance));
      CHECK(static_cast<int>(objs[0].id) == q + 1, msg_id);
      CHECK(std::fabs(objs[0].distance) < 1e-3, msg_d);
    }
  } catch (NGT::Exception &e) {
    std::fprintf(stderr, "FAIL: search error: %s\n", e.what());
    return 1;
  } catch (const std::exception &e) {
    std::fprintf(stderr, "FAIL: search std error: %s\n", e.what());
    return 1;
  }

  if (failures == 0) {
    std::printf("ngt test_package OK: ANNG index built & searched on OHOS\n");
    return 0;
  }
  std::fprintf(stderr, "ngt test_package FAILED (%d checks)\n", failures);
  return 1;
}
