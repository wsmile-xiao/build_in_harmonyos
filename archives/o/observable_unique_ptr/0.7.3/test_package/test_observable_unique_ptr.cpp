// test_package/test_observable_unique_ptr.cpp — observable_unique_ptr 0.7.3 消费者测试
//
// 通过 Conan 交付的 include/ 头文件真实使用 oup:: 公共 API；全部断言为显式检查 +
// 计数器（Release 下 NDEBUG 会把 assert() 编译掉 → 假绿，故不使用 assert()）。
// 每条断言逐行打印 [consumer] PASS/FAIL，末行打印 [consumer] TOTAL=<n> FAIL=<m>，
// 任一失败退出码非 0 —— 这就是 PR 正文「鸿蒙特有测试」行的取数位置。
//
// OUP_PKG_HEADER_PATH 由 test_package/CMakeLists.txt 传入（指向**交付进 conan 包的**
// 那一份头文件），前 3 条断言据此校验交付面，其余断言校验运行期语义。
#include <oup/observable_unique_ptr.hpp>

#include <cstdio>
#include <cstring>
#include <string>
#include <type_traits>
#include <utility>

static int g_total = 0;
static int g_failed = 0;

#define CHECK(cond)                                    \
    do {                                               \
        ++g_total;                                     \
        if (cond) {                                    \
            std::printf("[consumer] PASS  %s\n", #cond); \
        } else {                                       \
            ++g_failed;                                \
            std::printf("[consumer] FAIL  %s\n", #cond); \
        }                                              \
    } while (0)

#ifndef OUP_PKG_HEADER_PATH
#error "OUP_PKG_HEADER_PATH must be provided by test_package/CMakeLists.txt"
#endif

// ── 编译期断言（上游设计约束：编译不过即失败，不计入运行期计数）──
static_assert(!std::is_copy_constructible_v<oup::observable_unique_ptr<std::string>>,
              "unique ownership: not copyable");
static_assert(std::is_move_constructible_v<oup::observable_unique_ptr<std::string>>,
              "unique ownership: movable");
static_assert(std::is_copy_constructible_v<oup::observer_ptr<std::string>>,
              "observers are copyable");

// enable_observer_from_this 消费面：从成员函数内拿到观察者
struct node : oup::enable_observer_from_this_unique<node> {
    int v = 7;
};

int main() {
    // ── 交付面：包内头文件存在且是正确那一份（1-3）──
    std::FILE* fp = std::fopen(OUP_PKG_HEADER_PATH, "rb");
    CHECK(fp != nullptr);
    std::string header;
    if (fp) {
        char buf[4096];
        size_t n = 0;
        while ((n = std::fread(buf, 1, sizeof(buf), fp)) > 0) {
            header.append(buf, n);
        }
        std::fclose(fp);
    }
    CHECK(header.find("OBSERVABLE_UNIQUE_PTR_INCLUDED") != std::string::npos);
    CHECK(header.find("class basic_observable_ptr") != std::string::npos);

    // ── observable_sealed_ptr + observer_ptr 生命周期观察（4-10）──
    oup::observer_ptr<std::string> obs;
    {
        auto owner = oup::make_observable_sealed<std::string>("hello");
        CHECK(owner != nullptr);
        CHECK(*owner == std::string("hello"));
        obs = owner;
        CHECK(!obs.expired());
        CHECK(obs != nullptr);
        CHECK(obs.get() == owner.get());
    }
    CHECK(obs.expired());
    CHECK(obs == nullptr);

    // ── observable_unique_ptr：观察者拷贝/移动语义（11-13）──
    auto u = oup::make_observable_unique<int>(42);
    oup::observer_ptr<int> o1 = u;
    oup::observer_ptr<int> o2 = o1;
    CHECK(o1 == o2);
    CHECK(*o1 == 42);
    oup::observer_ptr<int> o3 = std::move(o2);
    CHECK(o3 == o1);

    // ── reset() 删除对象 → 观察者立即过期（14-15）──
    u.reset();
    CHECK(o1.expired());
    CHECK(o3 == nullptr);

    // ── release() 转移所有权：非 eoft 类型的观察者立即过期，对象归调用方（16-21）──
    auto r = oup::make_observable_unique<std::string>("release-me");
    oup::observer_ptr<std::string> ro = r;
    CHECK(!ro.expired());
    std::string* raw = r.release();
    CHECK(r == nullptr);
    CHECK(raw != nullptr);
    CHECK(raw->size() == 10);
    CHECK(ro.expired());
    delete raw;
    CHECK(ro.expired());

    // ── enable_observer_from_this：成员函数内取观察者（22-25）──
    oup::observer_ptr<node> nobs;
    {
        auto n = oup::make_observable_unique<node>();
        nobs   = n->observer_from_this();
        CHECK(!nobs.expired());
        CHECK(nobs.get() == n.get());
        CHECK(nobs->v == 7);
    }
    CHECK(nobs.expired());

    std::printf("[consumer] TOTAL=%d FAIL=%d\n", g_total, g_failed);
    return g_failed == 0 ? 0 : 1;
}
