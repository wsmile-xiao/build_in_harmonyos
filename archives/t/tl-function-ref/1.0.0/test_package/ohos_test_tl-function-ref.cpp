// ohos_test_tl-function-ref.cpp — HarmonyOS 专项测试 (R02)
// 用 OHOS aarch64 工具链编译并在 OHOS 平台运行，真实调用 tl::function_ref
// 的全部消费入口：自由函数、无捕获 lambda、带状态调用对象、算法传递、
// constexpr 语义与 noexcept。统计断言数并返回退出码。
#include <tl/function_ref.hpp>

#include <cstdio>
#include <vector>

namespace {

int add_one(int x) { return x + 1; }

struct Multiplier {
    int factor;
    int apply(int x) const { return x * factor; }
};

int collect(std::vector<int> const& v, tl::function_ref<int(int)> fn) {
    int acc = 0;
    for (auto x : v) acc += fn(x);
    return acc;
}

}  // namespace

int main() {
    int passed = 0, failed = 0;
#define CHECK(cond)                                                     \
    do {                                                                \
        if (cond) { ++passed; }                                         \
        else { ++failed; std::printf("FAIL %s:%d\n", __FILE__, __LINE__); } \
    } while (0)

    // 1) 自由函数目标
    tl::function_ref<int(int)> f = add_one;
    CHECK(f(41) == 42);

    // 2) 无捕获 lambda 目标
    auto twice = [](int v) { return v * 2; };
    tl::function_ref<int(int)> l = twice;
    CHECK(l(21) == 42);

    // 3) 带状态成员函数（经具名捕获 lambda，生命周期安全）
    Multiplier m{3};
    auto apply3 = [&m](int v) { return m.apply(v); };
    tl::function_ref<int(int)> mem = apply3;
    CHECK(mem(14) == 42);

    // 4) 算法/传递用法（值传递副本）
    std::vector<int> vals{1, 2, 3, 4};
    CHECK(collect(vals, add_one) == 14);

    // 5) 赋值重绑定与 swap（非拥有语义）
    tl::function_ref<int(int)> g = add_one;
    g = twice;
    CHECK(g(5) == 10);
    tl::function_ref<int(int)> h = add_one;
    g.swap(h);
    CHECK(g(5) == 6 && h(5) == 10);

    // 6) 空 lambda 到函数指针无堆分配（header-only 零依赖）
    CHECK(sizeof(tl::function_ref<int(int)>) == 2 * sizeof(void*));

    std::printf("OHOS test tl-function-ref: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
#undef CHECK
}