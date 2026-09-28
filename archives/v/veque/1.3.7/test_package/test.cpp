// test_package/test.cpp — veque 1.3.7 消费者真实用例（鸿蒙特有测试）
//
// 形态：#include <veque.hpp> + 实例化 veque::veque<T> 的读写 / 边界 / 迭代器真断言。
// 只编译不算测：每个 VP_CHECK 都是运行期断言，任一失败即 main 返回非 0，
// conan 的 test() 经 self.run（rc!=0 抛错）判失败（R34 / L0d 同口径）。
#include <veque.hpp>

#include <algorithm>
#include <cstdio>
#include <iterator>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>

static int g_checks = 0;
static int g_failures = 0;

#define VP_CHECK(cond)                                                        \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(cond)) {                                                        \
            ++g_failures;                                                     \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);       \
        }                                                                     \
    } while (0)

int main() {
    // ── A. 读写：两端插入、索引与 at() 读取、连续内存 ──────────────────────
    veque::veque<int> v;
    VP_CHECK(v.empty());
    VP_CHECK(v.size() == 0);

    for (int i = 0; i < 64; ++i) {
        v.push_back(i);
    }
    for (int i = 1; i <= 64; ++i) {
        v.push_front(-i);
    }
    VP_CHECK(v.size() == 128);
    VP_CHECK(v.front() == -64);
    VP_CHECK(v.back() == 63);
    VP_CHECK(v[0] == -64);
    VP_CHECK(v[127] == 63);
    VP_CHECK(v.at(0) == -64);
    VP_CHECK(v.at(70) == 6);          // 索引 0..63 = -64..-1，64..127 = 0..63
    VP_CHECK(v.data() != nullptr);

    bool at_throws = false;
    try {
        (void)v.at(v.size());
    } catch (const std::out_of_range &) {
        at_throws = true;
    }
    VP_CHECK(at_throws);

    bool contiguous = true;
    for (size_t i = 0; i < v.size(); ++i) {
        if (v.data()[i] != v[i]) {
            contiguous = false;
            break;
        }
    }
    VP_CHECK(contiguous);

    // 写路径：中段 insert / erase / 元素赋值
    auto it = v.insert(v.begin() + 64, 1000);
    VP_CHECK(*it == 1000);
    VP_CHECK(v.size() == 129);
    v.erase(v.begin() + 64);
    VP_CHECK(v.size() == 128);
    VP_CHECK(v[64] == 0);
    v[0] = -100;
    VP_CHECK(v.front() == -100);
    v.front() = -64;                  // 恢复原内容

    // ── B. 边界：前端扩容 / 容量族 / reserve 保持内容 ─────────────────────
    veque::veque<int> r;
    r.resize_front(10, 7);
    VP_CHECK(r.size() == 10);
    VP_CHECK(r.front() == 7);
    VP_CHECK(r.back() == 7);
    r.resize_back(20, 9);
    VP_CHECK(r.size() == 20);
    VP_CHECK(r.back() == 9);
    VP_CHECK(r.capacity_front() == r.size() + (r.capacity_full() - r.capacity_back()));
    VP_CHECK(r.capacity_back() >= r.size());
    VP_CHECK(r.capacity() >= 20);
    VP_CHECK(r.max_size() > r.size());

    const size_t before = r.size();
    r.reserve(16, 64);
    VP_CHECK(r.size() == before);
    VP_CHECK(r[0] == 7);
    VP_CHECK(r[19] == 9);
    VP_CHECK(r.capacity_front() >= 16);
    VP_CHECK(r.capacity_back() >= 64);
    VP_CHECK(r.capacity_front() + r.capacity_back() == r.size() + r.capacity_full());

    r.resize_front(0);
    VP_CHECK(r.empty());
    VP_CHECK(r.size() == 0);

    // ── C. 迭代器：正向 / 反向 / 随机访问 / 算法就地 ──────────────────────
    veque::veque<int> w;
    for (int i = 1; i <= 100; ++i) {
        w.push_back((i * 37) % 101);   // 1..100 的乱序置换（101 为质数）
    }
    VP_CHECK(w.end() - w.begin() == 100);
    VP_CHECK(w.cbegin() == w.begin());
    VP_CHECK(w.cend() == w.end());

    std::sort(w.begin(), w.end());
    VP_CHECK(std::is_sorted(w.begin(), w.end()));
    VP_CHECK(w.front() == 1);
    VP_CHECK(w.back() == 100);

    const veque::veque<int> &cv = w;
    const long forward_sum = std::accumulate(cv.begin(), cv.end(), 0L);
    VP_CHECK(forward_sum == 5050);

    const long reverse_sum = std::accumulate(w.rbegin(), w.rend(), 0L);
    VP_CHECK(reverse_sum == 5050);
    VP_CHECK(*w.rbegin() == 100);

    const auto found = std::find(w.begin(), w.end(), 42);
    VP_CHECK(found != w.end());
    VP_CHECK(*found == 42);
    VP_CHECK(std::count(w.begin(), w.end(), 42) == 1);

    veque::veque<int> mapped;
    mapped.reserve(w.size(), w.size());
    std::transform(w.begin(), w.end(), std::back_inserter(mapped),
                   [](int x) { return x * 2; });
    VP_CHECK(mapped.size() == 100);
    VP_CHECK(mapped.front() == 2);
    VP_CHECK(mapped.back() == 200);
    VP_CHECK(std::is_sorted(mapped.begin(), mapped.end()));

    // ── D. 非平凡类型 + C++17 强异常保证接口 + 拷贝/哈希/交换 ─────────────
    veque::veque<std::string> s;
    s.push_back("vector");
    s.emplace_back(3, 'x');
    s.push_front("double-ended ");
    VP_CHECK(s.size() == 3);
    VP_CHECK(s.front() == "double-ended ");
    VP_CHECK(s.back() == "xxx");
    VP_CHECK(s[1] == "vector");

    veque::veque<std::string> s2 = s;
    VP_CHECK(s2 == s);
    VP_CHECK(!(s2 != s));
    VP_CHECK(std::hash<veque::veque<std::string>>()(s2) ==
             std::hash<veque::veque<std::string>>()(s));

    const std::string popped = s2.pop_back_element();
    VP_CHECK(popped == "xxx");
    VP_CHECK(s2.size() == 2);
    VP_CHECK(s.size() == 3);          // 拷贝端操作不影响原容器

    const std::string popped_front = s2.pop_front_element();
    VP_CHECK(popped_front == "double-ended ");
    VP_CHECK(s2.size() == 1);
    VP_CHECK(s2.front() == "vector");

    veque::veque<std::string> swapped;
    swapped.swap(s);
    VP_CHECK(swapped.size() == 3);
    VP_CHECK(swapped.front() == "double-ended ");
    VP_CHECK(s.empty());              // s 原有 3 元素全部换出

    s.clear();
    VP_CHECK(s.empty());

    std::printf("VEQUE-CONSUMER checks=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
