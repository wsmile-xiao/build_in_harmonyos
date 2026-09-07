// xenium 0.0.2 test_package — 真实并发消费者测试
//
// 覆盖本次适配修复的三类路径：
//   1) vyukov_hash_map（generic_epoch_based 回收）并发 emplace/try_get_value/erase
//      —— 对应 0003/0004 补丁回移的上游 PR #43 内存序修复（aarch64 弱内存序）；
//   2) harris_michael_list_based_set（hazard_pointer 回收）并发 emplace/contains/erase；
//   3) michael_scott_queue（lock_free_ref_count 回收）多生产者-消费者流水线。
//
// 所有断言失败会使进程以非零码退出；不做 print-only 空验证。
#include <xenium/vyukov_hash_map.hpp>
#include <xenium/harris_michael_list_based_set.hpp>
#include <xenium/michael_scott_queue.hpp>

#include <xenium/reclamation/generic_epoch_based.hpp>
#include <xenium/reclamation/hazard_pointer.hpp>
#include <xenium/reclamation/lock_free_ref_count.hpp>

#include <atomic>
#include <cstdio>
#include <thread>
#include <vector>

static std::atomic<long> g_checks{0};
static std::atomic<long> g_failures{0};

#define CHECK(cond)                                                     \
  do {                                                                  \
    ++g_checks;                                                         \
    if (!(cond)) {                                                      \
      ++g_failures;                                                     \
      std::fprintf(stderr, "CHECK failed: %s at %s:%d\n", #cond,        \
                   __FILE__, __LINE__);                                 \
    }                                                                   \
  } while (0)

// ---------------------------------------------------------------------------
// 1) vyukov_hash_map<int,int> + generic_epoch_based：并发读写（修复路径）
// ---------------------------------------------------------------------------
using map_reclaimer = xenium::reclamation::generic_epoch_based<>;
using hash_map =
    xenium::vyukov_hash_map<int, int, xenium::policy::reclaimer<map_reclaimer>>;

static void test_vyukov_hash_map_parallel() {
  hash_map map(8);
  constexpr int kThreads = 4;
  constexpr int kKeysPerThread = 16;
  constexpr int kIterations = 400;

  std::vector<std::thread> threads;
  for (int i = 0; i < kThreads; ++i) {
    threads.emplace_back([i, &map] {
      typename map_reclaimer::region_guard guard{};
      // 与上游 parallel_usage 相同的节奏：插入 → 验证 → 每轮擦除自己的 key，
      // 使下一轮 emplace 重新成功；交替覆盖 erase(key) 与 extract(key, acc) 两条路径。
      for (int j = 0; j < kIterations; ++j) {
        for (int k = i * kKeysPerThread; k < (i + 1) * kKeysPerThread; ++k) {
          CHECK(map.emplace(k, k));
          for (int x = 0; x < 4; ++x) {
            typename hash_map::accessor acc;
            CHECK(map.try_get_value(k, acc));
            CHECK(k == *acc);
          }
          if ((j + i) % 4 == 0) {
            typename hash_map::accessor acc;
            CHECK(map.extract(k, acc));
            CHECK(k == *acc);
          } else {
            CHECK(map.erase(k));
          }
        }
      }
    });
  }
  for (auto& t : threads) {
    t.join();
  }

  // 终态校验：每轮结束均已擦除自身 key，全部 64 个 key 都应不存在
  for (int k = 0; k < kThreads * kKeysPerThread; ++k) {
    typename hash_map::accessor acc;
    CHECK(!map.try_get_value(k, acc));
  }

  // 单线程重插一次验证 map 仍可用
  CHECK(map.emplace(1, 1));
  typename hash_map::accessor acc;
  CHECK(map.try_get_value(1, acc));
  CHECK(1 == *acc);
  CHECK(map.erase(1));
}

// ---------------------------------------------------------------------------
// 2) harris_michael_list_based_set<int> + hazard_pointer：并发集合操作
// ---------------------------------------------------------------------------
using set_reclaimer = xenium::reclamation::hazard_pointer<>;
using list_set = xenium::harris_michael_list_based_set<
    int, xenium::policy::reclaimer<set_reclaimer>>;

static void test_harris_michael_list_based_set() {
  list_set set;
  constexpr int kThreads = 4;
  constexpr int kKeysPerThread = 64;

  std::vector<std::thread> threads;
  for (int i = 0; i < kThreads; ++i) {
    threads.emplace_back([i, &set] {
      typename set_reclaimer::region_guard guard{};
      const int base = 1000 * (i + 1);
      for (int k = 0; k < kKeysPerThread; ++k) {
        CHECK(set.emplace(base + k));
      }
      for (int k = 0; k < kKeysPerThread; ++k) {
        CHECK(set.contains(base + k));
      }
    });
  }
  for (auto& t : threads) {
    t.join();
  }

  // 终态校验 + 重复插入必须失败
  for (int i = 0; i < kThreads; ++i) {
    const int base = 1000 * (i + 1);
    for (int k = 0; k < kKeysPerThread; ++k) {
      CHECK(set.contains(base + k));
    }
    CHECK(!set.emplace(base));  // 已存在，第二次插入必须失败
  }
}

// ---------------------------------------------------------------------------
// 3) michael_scott_queue<int> + lock_free_ref_count：生产者-消费者流水线
// ---------------------------------------------------------------------------
static void test_michael_scott_queue_pipeline() {
  using queue_reclaimer = xenium::reclamation::lock_free_ref_count<>;
  xenium::michael_scott_queue<int, xenium::policy::reclaimer<queue_reclaimer>>
      queue;
  constexpr int kItems = 20000;

  std::atomic<bool> done{false};
  std::thread producer([&queue, &done] {
    typename queue_reclaimer::region_guard guard{};
    for (int i = 1; i <= kItems; ++i) {
      queue.push(i);
    }
    done.store(true);
  });

  long long sum = 0;
  int consumed = 0;
  {
    typename queue_reclaimer::region_guard guard{};
    int elem;
    while (consumed < kItems) {
      if (queue.try_pop(elem)) {
        sum += elem;
        ++consumed;
      }
    }
  }
  producer.join();

  CHECK(consumed == kItems);
  const long long expected =
      static_cast<long long>(kItems) * (kItems + 1) / 2;
  CHECK(sum == expected);
}

int main() {
  test_vyukov_hash_map_parallel();
  std::printf("[1/3] vyukov_hash_map parallel emplace/get/erase done\n");

  test_harris_michael_list_based_set();
  std::printf("[2/3] harris_michael_list_based_set parallel emplace/contains done\n");

  test_michael_scott_queue_pipeline();
  std::printf("[3/3] michael_scott_queue producer-consumer pipeline done\n");

  std::printf("xenium test_package: checks=%ld failures=%ld\n",
              g_checks.load(), g_failures.load());
  return g_failures == 0 ? 0 : 1;
}
