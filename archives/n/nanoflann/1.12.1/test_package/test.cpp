// test_package/test.cpp — nanoflann 1.12.1 consumer kNN search
// Bootstrap skeleton; uses the packaged header for a real KD-tree search.
#include "nanoflann.hpp"

#include <cassert>
#include <cmath>
#include <vector>

// Minimal point cloud adapter required by nanoflann
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

int main() {
  PointCloud cloud;
  cloud.pts = {{0.0, 0.0}, {1.0, 1.0}, {2.0, 2.0}, {3.0, 3.0}};

  using KDTree =
      nanoflann::KDTreeSingleIndexAdaptor<
          nanoflann::L2_Simple_Adaptor<double, PointCloud>, PointCloud, 2>;
  KDTree index(2, cloud, nanoflann::KDTreeSingleIndexAdaptorParams(10));
  index.buildIndex();

  const double query[2] = {1.1, 1.0};
  size_t ret_index = 0;
  double out_dist_sqr = 0.0;
  nanoflann::KNNResultSet<double> result_set(1);
  result_set.init(&ret_index, &out_dist_sqr);
  index.findNeighbors(result_set, query);

  // nearest of {(0,0),(1,1),(2,2),(3,3)} to (1.1,1.0) is (1,1), index 1
  assert(ret_index == 1);
  assert(std::abs(out_dist_sqr - 0.01) < 1e-9);

  return 0;
}