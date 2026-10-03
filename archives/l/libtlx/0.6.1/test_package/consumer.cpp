// consumer.cpp — libtlx 0.6.1 已安装包消费者测试（只 find_package(tlx) → tlx::tlx）
// 期望值全部来自上游 tests/ 原生真跑探针 + python hashlib 交叉验证（零猜测）。
// 末尾打印 PASS 汇总行供判读。
#include <tlx/version.hpp>
#include <tlx/digest/md5.hpp>
#include <tlx/digest/sha1.hpp>
#include <tlx/digest/sha256.hpp>
#include <tlx/digest/sha512.hpp>
#include <tlx/string.hpp>
#include <tlx/string/base64.hpp>
#include <tlx/string/ssprintf.hpp>
#include <tlx/container/btree_set.hpp>
#include <tlx/container/btree_map.hpp>
#include <tlx/container/lru_cache.hpp>
#include <tlx/container/ring_buffer.hpp>
#include <tlx/container/splay_tree.hpp>
#include <tlx/counting_ptr.hpp>
#include <tlx/thread_pool.hpp>
#include <tlx/siphash.hpp>
#include <tlx/multi_timer.hpp>
#include <tlx/timestamp.hpp>
#include <tlx/math/integer_log2.hpp>
#include <tlx/sort/parallel_mergesort.hpp>
#include <tlx/algorithm/multiway_merge.hpp>

#include <atomic>
#include <cstdio>
#include <string>
#include <thread>
#include <utility>
#include <vector>

static int g_checks = 0;
static int g_fails = 0;
#define CHECK(cond)                                                          \
  do {                                                                       \
    ++g_checks;                                                              \
    if (!(cond)) {                                                           \
      ++g_fails;                                                             \
      std::printf("[consumer][FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond); \
    }                                                                        \
  } while (0)

#define CHECK_EQ(a, b)                                                       \
  do {                                                                       \
    ++g_checks;                                                              \
    if (!((a) == (b))) {                                                     \
      ++g_fails;                                                             \
      std::printf("[consumer][FAIL] %s:%d: %s == %s\n",                      \
                  __FILE__, __LINE__, #a, #b);                               \
    }                                                                        \
  } while (0)

// 计数对象（侵入式引用计数，上游 counting_ptr_test 同构）
struct MyInt : public tlx::ReferenceCounter {
    int i;
    explicit MyInt(int x) : i(x) { }
};

static void test_version() {
    // 上游 version.hpp：0.6.1 / 20230523 / (0*100+6)*100000000+1
    CHECK_EQ(TLX_MAJOR_VERSION, 0);
    CHECK_EQ(TLX_MINOR_VERSION, 6);
    CHECK_EQ(TLX_PATCH_VERSION, 1);
    CHECK_EQ(TLX_DATE_VERSION, 20230523);
    CHECK_EQ(TLX_VERSION, 600000001ull);
}

static void test_digest() {
    // RFC 1321 / 6234 标准向量（python hashlib 交叉验证一致）
    CHECK(tlx::md5_hex("abc") == "900150983cd24fb0d6963f7d28e17f72");
    CHECK(tlx::md5_hex("") == "d41d8cd98f00b204e9800998ecf8427e");
    CHECK(tlx::sha1_hex("abc") == "a9993e364706816aba3e25717850c26c9cd0d89d");
    CHECK(tlx::sha256_hex("abc") ==
          "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    CHECK(tlx::sha256_hex("") ==
          "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    CHECK(tlx::sha512_hex("abc") ==
          "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
          "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f");
}

static void test_string() {
    // 期望值 = 上游 string_test.cpp 断言 + 探针实测
    auto sv = tlx::split('/', "/usr/bin/test/");
    CHECK_EQ(sv.size(), 5u);
    CHECK(sv[1] == "usr" && sv[2] == "bin" && sv[3] == "test");
    sv = tlx::split('/', "/usr/bin/test", 3);
    CHECK_EQ(sv.size(), 3u);
    CHECK(sv[2] == "bin/test");
    sv = tlx::split('/', "/usr//bin/test", 0);
    CHECK_EQ(sv.size(), 0u);
    sv = tlx::split("/", "/usr/bin/test");
    CHECK_EQ(sv.size(), 4u);
    CHECK(tlx::trim("  abc  ") == "abc");
    CHECK(tlx::to_upper("aBc") == "ABC");
    CHECK(tlx::to_lower("aBc") == "abc");
    CHECK(tlx::starts_with("abcdef", "abc"));
    CHECK(tlx::ends_with("abcdef", "def"));
    CHECK(tlx::join(':', std::vector<std::string>{"a", "b", "c"}) == "a:b:c");
    CHECK(tlx::ssprintf("%d-%s-%03d", 42, "x", 7) == "42-x-007");
    CHECK(tlx::base64_encode("Hello, tlx!") == "SGVsbG8sIHRseCE=");
    CHECK(tlx::base64_encode("foo") == "Zm9v");
    CHECK(tlx::base64_decode("SGVsbG8sIHRseCE=") == "Hello, tlx!");
    CHECK(tlx::base64_decode("Zm9vYg==") == "foob");
    // 上游 string_test 期望
    CHECK(tlx::escape_uri("hello <tag>\"") == "hello%20%3Ctag%3E%22");
    CHECK(tlx::escape_html("hello <tag> \"abc\" & \"def\"") ==
          "hello &lt;tag&gt; &quot;abc&quot; &amp; &quot;def&quot;");
}

static void test_math() {
    CHECK_EQ(tlx::integer_log2_floor(64), 6u);
    CHECK_EQ(tlx::integer_log2_ceil(64), 6u);
    CHECK_EQ(tlx::integer_log2_floor(65), 6u);
    CHECK_EQ(tlx::integer_log2_ceil(65), 7u);
    CHECK_EQ(tlx::integer_log2_floor(1), 0u);
}

static void test_containers() {
    tlx::btree_set<unsigned> bs;
    for (unsigned i = 0; i < 3200; ++i) {
        bs.insert(i % 100);
    }
    CHECK_EQ(bs.count(42u), 1u);
    CHECK(bs.find(42u) != bs.end());
    CHECK_EQ(bs.erase(42u), 1u);
    CHECK_EQ(bs.count(42u), 0u);

    tlx::btree_map<int, int> bm;
    bm[42] = 24;
    CHECK_EQ(bm.find(42)->second, 24);
    CHECK(bm.find(99) == bm.end());
    CHECK_EQ(bm.erase(42), 1u);
    CHECK_EQ(bm.size(), 0u);

    tlx::LruCacheSet<size_t> lrus;
    lrus.put(7);
    CHECK(lrus.exists(7));
    CHECK_EQ(lrus.size(), 1u);

    tlx::LruCacheMap<size_t, size_t> lrum;
    lrum.put(1, 10);
    lrum.put(2, 20);
    CHECK(lrum.exists(1));
    CHECK_EQ(lrum.size(), 2u);
    auto kvp = lrum.pop();  // LRU 序：先弹出最久未用
    CHECK_EQ(kvp.first, 1u);
    CHECK_EQ(kvp.second, 10u);

    tlx::RingBuffer<size_t> ring(10);
    CHECK_EQ(ring.size(), 0u);
    ring.push_back(0);
    for (size_t i = 1; i < 10; ++i)
        ring.emplace_back(i);
    CHECK_EQ(ring.size(), 10u);
    for (size_t i = 0; i < ring.size(); ++i)
        CHECK_EQ(ring[i], i);

    tlx::SplayTree<size_t> st;
    CHECK(st.insert(7));       // 新键 → true
    CHECK(!st.insert(7));      // 重复键 → false
    CHECK_EQ(st.find(7)->key, 7u);  // splay find：命中节点 key 精确匹配
    CHECK_EQ(st.size(), 1u);
}

static void test_counting_ptr() {
    auto p1 = tlx::make_counting<MyInt>(42);
    CHECK_EQ(p1->i, 42);
    CHECK(p1->unique());
    auto p2 = p1;
    CHECK(!p1->unique());
    CHECK(p2 == p1);
    CHECK_EQ(p1->reference_count(), 2u);
}

static void test_threading() {
    // ThreadPool：100 个原子递增任务全部执行
    std::atomic<int> c{0};
    {
        tlx::ThreadPool pool(4);
        for (int i = 0; i < 100; ++i)
            pool.enqueue([&] { ++c; });
        pool.loop_until_empty();
    }
    CHECK_EQ(c.load(), 100);

    // MultiTimer：相位计时 API 可用且非负
    tlx::MultiTimer mt;
    mt.start("phase1");
    mt.stop();
    mt.start("phase2");
    mt.stop();
    CHECK(mt.get("phase1") >= 0.0);
    CHECK(mt.total() >= 0.0);

    // timestamp：单调时钟可用
    double t0 = tlx::timestamp();
    CHECK(t0 > 0.0);
    CHECK(tlx::timestamp() >= t0);
}

static void test_siphash() {
    // 上游 siphash_test.cpp test_vectors_data 前 3 个向量（key=0..15, msg=i..）
    unsigned char key[16], msg[64];
    for (int i = 0; i < 16; ++i) key[i] = (unsigned char)i;
    for (int i = 0; i < 64; ++i) msg[i] = (unsigned char)i;
    CHECK_EQ(tlx::siphash(key, msg, 0), 0x726fdb47dd0e0e31ull);
    CHECK_EQ(tlx::siphash(key, msg, 6), 0xcbc9466e58fee3ceull);
    CHECK_EQ(tlx::siphash(key, msg, 8), 0x93f5f5799a932462ull);
    CHECK_EQ(tlx::siphash_plain(key, msg, 8), 0x93f5f5799a932462ull);
}

static void test_sort_merge() {
    // parallel_mergesort（并行归并排序，libtlx.a 编译单元覆盖路径）
    std::vector<int> v = {5, 3, 8, 1, 9, 2, 7, 4, 6, 0};
    tlx::parallel_mergesort(v.begin(), v.end(), std::less<int>(), 2);
    bool sorted = true;
    for (size_t i = 1; i < v.size(); ++i)
        if (v[i - 1] > v[i]) sorted = false;
    CHECK(sorted);
    CHECK_EQ(v.front(), 0);
    CHECK_EQ(v.back(), 9);

    // multiway_merge（两路有序序列归并）
    std::vector<int> a = {1, 3, 5, 7}, b = {2, 4, 6, 8};
    std::vector<std::pair<std::vector<int>::iterator,
                          std::vector<int>::iterator>> seqs = {
        {a.begin(), a.end()}, {b.begin(), b.end()}};
    std::vector<int> out(8);
    auto it = tlx::multiway_merge(seqs.begin(), seqs.end(), out.begin(), 8);
    CHECK(it == out.begin() + 8);
    bool merged = true;
    for (int i = 0; i < 8; ++i)
        if (out[i] != i + 1) merged = false;
    CHECK(merged);
}

int main() {
    test_version();
    test_digest();
    test_string();
    test_math();
    test_containers();
    test_counting_ptr();
    test_threading();
    test_siphash();
    test_sort_merge();

    if (g_fails == 0) {
        std::printf("consumer: PASS %d/%d assertions\n", g_checks, g_checks);
        return 0;
    }
    std::printf("consumer: FAIL %d/%d assertions\n",
                g_checks - g_fails, g_checks);
    return 1;
}
