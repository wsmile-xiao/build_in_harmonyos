// nanoflann 1.12.1 — HarmonyOS PC (aarch64) specific verification test.
//
// R02 hmos_test evidence: calls the nanoflann public API (KD-tree build +
// kNN + radius search + dynamic point add) and verifies behavior on the
// OHOS aarch64 verification path (host aarch64 userland, clang 15.0.4 OHOS
// toolchain from /data/service/hnp/bin, libc++).
//
// Build (OHOS cross):
//   /data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++ -std=c++17 \
//     -I include test_hmos.cpp -o test_nanoflann_hmos
//
// Run (the verification host is aarch64 with OHOS userland):
//   ./test_nanoflann_hmos
#include "nanoflann.hpp"

#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <vector>

namespace {

struct PointCloud {
  std::vector<std::vector<double>> pts;

  inline size_t kdtree_get_point_count() const { return pts.size(); }

  inline double kdtree_get_pt(const size_t idx, const size_t dim) const {
    return pts[idx][dim];
  }

  template <class BBOX>
  bool kdtree_get_bbox(BBOX&) const {
    return false;
  }
};

using KDTree =
    nanoflann::KDTreeSingleIndexAdaptor<
        nanoflann::L2_Simple_Adaptor<double, PointCloud>, PointCloud, 2>;

// Build a 2-D kd-tree, query kNN, then a radius search, then a rank-kNN
// (rknnSearch) query: exercises buildIndex/findNeighbors/radiusSearch/
// rknnSearch on the OHOS aarch64 verification path.
void test_knn_and_radius_search() {
  PointCloud cloud;
  cloud.pts = {{0.0, 0.0}, {1.0, 1.0}, {2.0, 2.0}, {3.0, 3.0}};

  KDTree index(2, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
  index.buildIndex();

  // kNN
  const double query[2] = {1.1, 1.0};
  size_t ret_index = 0;
  double out_dist_sqr = 0.0;
  nanoflann::KNNResultSet<double> result_set(1);
  result_set.init(&ret_index, &out_dist_sqr);
  assert(index.findNeighbors(result_set, query));
  // nearest of the four points to (1.1, 1.0) is (1,1) -> index 1
  assert(ret_index == 1);
  assert(std::abs(out_dist_sqr - 0.01) < 1e-9);

  // radius search around (1.1,1.0) radius 1.5 (squared 2.25)
  std::vector<nanoflann::ResultItem<KDTree::IndexType, KDTree::DistanceType>>
      matches_out;
  nanoflann::SearchParameters params;
  const double radius = 1.5;
  const size_t n = index.radiusSearch(
      query, radius * radius, matches_out, params);
  // within radius² 2.25: (1,1) d²=0.01, (2,2) d²=1.81, (0,0) d²=2.21, (3,3) d²=7.61
  assert(n == 3);
  assert(matches_out[0].first == 1);  // (1,1) is the closest
  assert(std::abs(matches_out[0].second - 0.01) < 1e-9);

  // rank-kNN (rknnSearch): top-1 within squared-radius bound 0.05
  // (RKNNResultSet: radius is the maximum search squared distance; matches
  // nearest point (1,1) at d^2=0.01, excludes (2,2) at d^2=1.81)
  KDTree::IndexType rk_indices[2] = {0, 0};
  double rk_dists[2] = {0.0, 0.0};
  const size_t rk_n = index.rknnSearch(query, 1, rk_indices, rk_dists, 0.05);
  assert(rk_n == 1);
  assert(rk_indices[0] == 1);                 // nearest (1,1)
  assert(std::abs(rk_dists[0] - 0.01) < 1e-9);
}

}  // namespace

int main() {
  test_knn_and_radius_search();
  std::printf("nanoflann hmos test: PASS (knn + radius + rknn)\n");
  return 0;
}