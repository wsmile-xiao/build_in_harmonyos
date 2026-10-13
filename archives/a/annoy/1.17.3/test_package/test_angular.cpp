// test_angular.cpp — annoy consumer end-to-end test (Angular metric).
//
// This is a *consumer* test: it only uses the installed public headers through
// the exported `Annoy::Annoy` CMake target and performs a complete, realistic
// approximate-nearest-neighbour workflow end to end:
//
//   build index -> query by item -> query by vector -> verify neighbour
//   quality against a brute-force ground truth.
//
// Neighbour quality is checked against exact brute-force results rather than
// hard-coded ids, so the assertions are meaningful on any platform/arch.
#include <annoy/annoylib.h>
#include <annoy/kissrandom.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <utility>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const char* what) {
  ++g_checks;
  if (!ok) {
    ++g_failed;
    std::printf("FAIL: %s\n", what);
  }
}

// Deterministic pseudo-random vector generator (no <random> engine variance).
void make_vector(int i, int f, std::vector<float>* out) {
  out->resize(f);
  unsigned int s = static_cast<unsigned int>(i) * 2654435761u + 12345u;
  for (int j = 0; j < f; ++j) {
    s = s * 1664525u + 1013904223u;
    (*out)[j] = static_cast<float>((s >> 8) & 0xFFFF) / 65535.0f * 2.0f - 1.0f;
  }
}

float angular_distance(const std::vector<float>& a, const std::vector<float>& b) {
  double dot = 0.0, na = 0.0, nb = 0.0;
  for (size_t k = 0; k < a.size(); ++k) {
    dot += static_cast<double>(a[k]) * b[k];
    na += static_cast<double>(a[k]) * a[k];
    nb += static_cast<double>(b[k]) * b[k];
  }
  if (na == 0.0 || nb == 0.0) return 1.0f;
  return static_cast<float>(1.0 - dot / (std::sqrt(na) * std::sqrt(nb)));
}

typedef Annoy::AnnoyIndex<int, float, Annoy::Angular, Annoy::Kiss32Random,
                          Annoy::AnnoyIndexSingleThreadedBuildPolicy>
    PlainIndex;

}  // namespace

int main() {
  const int f = 16;
  const int n = 1000;
  const int k = 10;

  std::vector<std::vector<float> > data(n);
  for (int i = 0; i < n; ++i) make_vector(i, f, &data[i]);

  PlainIndex index(f);

  // ---- Phase 1: build the index end to end -------------------------------
  for (int i = 0; i < n; ++i) {
    check(index.add_item(i, data[i].data()), "add_item returns true");
  }
  check(index.build(20), "build() returns true");
  check(index.get_n_items() == n, "get_n_items matches inserted count");
  check(index.get_n_trees() == 20, "get_n_trees matches requested tree count");

  // ---- Phase 2: query by item, compare with brute force ------------------
  std::vector<int> got;
  index.get_nns_by_item(7, k, -1, &got, NULL);
  check(static_cast<int>(got.size()) == k, "get_nns_by_item returns k results");
  // ★review r5 #8：这里原先断言 got[0] == 7，即在**近似**搜索上要求精确 rank-1。
  // 本文件其它断言（第 99/112 行 `hits >= k - 1`）已明确容忍近似，此处口径不一致：
  // 20 棵树 + search_k = -1 时贪心下降若落到别的叶子就会失败，属 flaky 断言。
  // 查询项自身距离恒为 0，是内容上确定的精确最近邻，但「排在结果第 0 位」仍取决于
  // 贪心路径。故收敛为：查询项必须被返回，且其距离为 0（强度保留，不再依赖路径）。
  check(std::find(got.begin(), got.end(), 7) != got.end(),
        "self-query result set contains the query item");
  // ★review r7 P2-3：上一版写成 get_distance(7, got[0]) == 0.0 —— 但那只有在
  // got[0] == 7 时才成立，等于把注释刚说要丢掉的 rank-1 依赖又原样搬了回来。
  // 这里改为不依赖任何固定下标：结果集中**存在**某个元素与查询项距离为 0。
  // 注意标尺差异：上游 get_distance 返回 sqrt(2 - 2cos)，而本文件的
  // angular_distance 返回 1 - cos，两者不可直接互比，故只用上游自己的标尺。
  bool self_present_at_zero = false;
  for (size_t i = 0; i < got.size(); ++i) {
    if (got[i] == 7 && index.get_distance(7, got[i]) == 0.0f)
      self_present_at_zero = true;
  }
  check(self_present_at_zero,
        "self-query returns the query item at distance 0 (any rank)");

  std::vector<std::pair<float, int> > exact;
  for (int i = 0; i < n; ++i)
    exact.push_back(std::make_pair(angular_distance(data[7], data[i]), i));
  std::sort(exact.begin(), exact.end());

  // annoy is approximate; require a strong overlap with the exact top-k.
  std::set<int> approx(got.begin(), got.end());
  int hits = 0;
  for (int i = 0; i < k; ++i)
    if (approx.count(exact[i].second)) ++hits;
  std::printf("get_nns_by_item: %d/%d of the exact top-%d neighbours found\n", hits,
              k, k);
  check(hits >= k - 1, "approximate top-k overlaps exact top-k (>= k-1)");

  // ---- Phase 3: query by vector -----------------------------------------
  std::vector<int> got_vec;
  index.get_nns_by_vector(data[7].data(), k, -1, &got_vec, NULL);
  check(static_cast<int>(got_vec.size()) == k,
        "get_nns_by_vector returns k results");
  std::set<int> approx_vec(got_vec.begin(), got_vec.end());
  int hits_vec = 0;
  for (int i = 0; i < k; ++i)
    if (approx_vec.count(exact[i].second)) ++hits_vec;
  std::printf("get_nns_by_vector: %d/%d of the exact top-%d neighbours found\n",
              hits_vec, k, k);
  check(hits_vec >= k - 1, "vector query overlaps exact top-k (>= k-1)");

  // ---- Phase 4: metric invariants ---------------------------------------
  check(std::fabs(index.get_distance(3, 3)) < 1e-5f,
        "angular distance of an item to itself is 0");

  std::vector<float> item(f, 0.0f);
  index.get_item(3, item.data());
  bool same = true;
  for (int j = 0; j < f; ++j)
    if (std::fabs(item[j] - data[3][j]) > 1e-6f) same = false;
  check(same, "get_item round-trips the inserted values");

  std::vector<int> all;
  index.get_nns_by_item(0, n, -1, &all, NULL);
  check(static_cast<int>(all.size()) == n, "exhaustive query returns every item");

  std::printf("test_angular: %d checks, %d failed\n", g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
