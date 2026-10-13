// test_ondisk.cpp — annoy consumer end-to-end test (save/load + mmap + threads).
//
// Consumer test for the OHOS-relevant code paths of the installed headers:
//
//   * multithreaded build policy (ANNOYLIB_MULTITHREADED_BUILD ->
//     std::thread / std::shared_mutex, hence the pthread requirement);
//   * save()/load() of a real index file on disk, i.e. the mmap-based
//     on-disk-build path of annoylib.h that OHOS resolves via <sys/mman.h>;
//   * a second consumer instance re-opening the persisted index and returning
//     the same neighbours as the producer.
#include <annoy/annoylib.h>
#include <annoy/kissrandom.h>

#include <unistd.h>  // getpid(): run-unique on-disk index path (review r5 #4)

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

// ★review r9 P1-1：r5 #6 让 check() 失败即 std::exit(1)，而 std::exit **不会**
// 执行 main 末尾的清理、也不会展开作用域 —— 于是每条失败路径都会残留落盘索引，
// 而失败路径恰恰是最需要清理的地方（这正是 r5 #4 想避免的）。std::exit 会执行
// atexit 处理器，故用它把清理做成 exit-proof；RAII 守卫在这里无效（析构被跳过）。
std::string g_tree_path;

void remove_tree_file() {
  if (!g_tree_path.empty()) std::remove(g_tree_path.c_str());
}


// ★review r5 #6：check() 早先只累加计数、从不中止。load() 失败会返回 false 且
// 内部 _nodes 仍为 NULL，后续 get_n_items()/get_nns_by_item()/get_item() 会直接
// 解引用 NULL → SIGSEGV，真实根因（save/load 失败）被崩溃掩盖，也走不到
// `g_failed != 0` 的正常退出路径。失败即 fatal，保证退出码与失败原因都可见。
void check(bool ok, const char* what) {
  ++g_checks;
  if (!ok) {
    ++g_failed;
    std::printf("FAIL: %s\n", what);
    std::fflush(stdout);
    std::exit(1);
  }
}

void make_vector(int i, int f, std::vector<double>* out) {
  out->resize(f);
  unsigned int s = static_cast<unsigned int>(i) * 40503u + 7u;
  for (int j = 0; j < f; ++j) {
    s = s * 1103515245u + 12345u;
    (*out)[j] = static_cast<double>((s >> 9) & 0xFFFF) / 65535.0;
  }
}

typedef Annoy::AnnoyIndex<int, double, Annoy::Euclidean, Annoy::Kiss32Random,
                          Annoy::AnnoyIndexMultiThreadedBuildPolicy>
    ThreadedIndex;

}  // namespace

int main(int argc, char** argv) {
  // ★review r5 #4：落盘路径改为 run-unique 并且结束时删除。此前是固定相对名
  // `annoy_ondisk_test.tree`，而 CWD 由 Conan 的 self.run() 决定、不受本测试控制：
  // 上一轮残留的文件会让 load() 读到**陈旧索引**，使 before == after 之类的断言
  // 与本轮构建无关 —— 测试因此不是 hermetic 的。
  std::ostringstream path_ss;
  if (argc > 1) {
    path_ss << argv[1];
  } else {
    path_ss << "annoy_ondisk_test." << static_cast<long>(::getpid()) << ".tree";
  }
  const std::string path = path_ss.str();
  g_tree_path = path;
  std::atexit(remove_tree_file);
  const int f = 24;
  const int n = 2000;
  const int k = 8;

  std::vector<std::vector<double> > data(n);
  for (int i = 0; i < n; ++i) make_vector(i, f, &data[i]);

  std::vector<int> before;
  int producer_trees = 0;

  // ---- Producer: build with the multithreaded policy, then persist -------
  {
    ThreadedIndex index(f);
    for (int i = 0; i < n; ++i)
      check(index.add_item(i, data[i].data()), "add_item returns true");
    check(index.get_n_items() == n, "get_n_items matches inserted count");

    // ★review r5 #5/#7 + r9 P2-1：这里原先的注释说「树数取决于
    // hardware_concurrency()，不等于 q」，据此只断言了 `> 0`。该说法是错的：
    // 上游把 q 按 trees_per_thread = floor((q + thread_idx) / n_threads) 分给
    // 各线程，求和**恰好等于 q**（余数之和 < n_threads），上游自己的 n_jobs
    // 测试就断言 n_trees == q。错误注释正是弱断言的唯一依据。
    // r9 又指出：上一版注释声称「已显式传线程数」，但调用其实是 build(15)，
    // 上游 build(q, n_threads = -1, ...) 在 -1 时取 hardware_concurrency()，
    // 即那条路径仍被走到。现在**真的**显式传一个小的固定线程数，
    // 既让注释与代码一致，也消除对宿主核数的依赖
    //（≥64 核机器上 pthread_create EAGAIN 会 std::terminate）。
    check(index.build(15, 2), "multithreaded build(15, n_threads=2) returns true");
    producer_trees = index.get_n_trees();
    check(index.get_n_trees() == 15,
          "multithreaded build(15, 2) produces exactly 15 trees");

    index.get_nns_by_item(42, k, -1, &before, NULL);
    check(static_cast<int>(before.size()) == k,
          "threaded in-memory query returns k results");

    check(index.save(path.c_str(), /*prefault=*/true),
          "save() writes the index to disk");
    index.unload();
  }

  // ---- Consumer: re-open the persisted index and re-run the query --------
  {
    ThreadedIndex index(f);
    check(index.load(path.c_str(), /*prefault=*/true),
          "load() mmaps the persisted index");
    check(index.get_n_items() == n,
          "loaded index reports the original item count");
    check(index.get_n_trees() == producer_trees,
          "loaded index preserves the tree count written by the producer");

    std::vector<int> after;
    index.get_nns_by_item(42, k, -1, &after, NULL);
    check(static_cast<int>(after.size()) == k,
          "loaded index query returns k results");
    check(before == after,
          "load() round-trip returns identical neighbours to the producer");

    // Distance/metric still behaves after an mmap-backed load.
    check(index.get_distance(42, 42) == 0.0,
          "euclidean distance of an item to itself is 0 after load");

    std::vector<double> v(f, 0.0);
    index.get_item(100, v.data());
    bool same = true;
    for (int j = 0; j < f; ++j)
      if (std::fabs(v[j] - data[100][j]) > 1e-9) same = false;
    check(same, "get_item after load round-trips the inserted values");

    // A second, wider result set computed after the mmap load must still be
    // valid and contain the query item itself.
    std::vector<int> wide;
    index.get_nns_by_item(100, 50, -1, &wide, NULL);
    std::set<int> wide_set(wide.begin(), wide.end());
    check(wide_set.count(100) == 1,
          "wide query after load contains the query item itself");
    index.unload();
  }

  // ★review r5 #4（后半）+ r9 P1-1：删除本次落盘的索引，避免污染 CI 工作目录、
  // 也避免下一轮被误当作有效输入。路径是 run-unique 的，删错也不会伤到别的 run。
  // 此处保留显式删除（正常路径立即回收）；失败路径由上面的 atexit 处理器兜底，
  // 重复删除无害。
  std::remove(path.c_str());

  std::printf("test_ondisk: %d checks, %d failed\n", g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
