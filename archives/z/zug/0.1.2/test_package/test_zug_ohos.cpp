// zug 鸿蒙专项测试：跨翻译单元使用类型擦除管道 + 管道状态隔离 + 深实例化。
// 与 test_zug 分开编译到两个 .cpp，真正的检查点是「另一个 TU 里实例化的
// zug 模板在 OHOS 运行时（musl + libc++ + clang15）能与本 TU 一致工作」。
#include <zug/compose.hpp>
#include <zug/into_vector.hpp>
#include <zug/transducer/filter.hpp>
#include <zug/transducer/map.hpp>
#include <zug/transducer/range.hpp>
#include <zug/transducer/transducer.hpp>
#include <zug/transduce.hpp>

#include <functional>
#include <iostream>
#include <string>
#include <vector>

std::vector<std::string> zug_ohos_apply(zug::transducer<int, std::string> &xform,
                                        const std::vector<int> &in);
std::vector<int> zug_ohos_reused_pipeline(const std::vector<int> &in);

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const char *what)
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
        std::cerr << "FAIL: " << what << std::endl;
    }
}

} // namespace

int main()
{
    auto xform = zug::transducer<int, std::string>{
        zug::comp(zug::filter([](int x) { return x % 2 == 0; }),
                  zug::map([](int x) { return std::to_string(x); }))};

    // 1) 管道在本 TU 构造，转导在另一个 TU 完成
    auto input = std::vector<int>{1, 2, 3, 4};
    check(zug_ohos_apply(xform, input) == (std::vector<std::string>{"2", "4"}),
          "type-erased xform applied across translation units");

    // 2) 同一管道在本 TU 直接转导，结果必须与跨 TU 一致
    auto even = std::vector<int>{2, 6, 7};
    check(zug::into_vector(xform, even) == (std::vector<std::string>{"2", "6"}),
          "same xform yields same result in this TU");

    // 3) 跨 TU 复用无状态管道
    auto small = std::vector<int>{1, 2, 3};
    check(zug_ohos_reused_pipeline(small) == (std::vector<int>{4, 6}),
          "reused pipeline result");
    check(zug_ohos_reused_pipeline(small) == zug_ohos_reused_pipeline(small),
          "pipeline carries no mutable state across runs");

    // 4) 深实例化：101 个元素走 map/filter 链后用 std::plus 折叠
    auto many = zug::into_vector(zug::range(0, 101));
    check(many.size() == 101, "range(0,101) length");
    check(zug::transduce(zug::map([](int x) { return x; }),
                         std::plus<int>{}, 0, many)
              == 5050,
          "fold 0..100 through a mapped pipeline");

    std::cout << "test_zug_ohos: " << (g_checks - g_failed) << "/" << g_checks
              << " assertions passed (cxx=" << __cplusplus
              << ", sizeof(void*)=" << sizeof(void*) << ")" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
