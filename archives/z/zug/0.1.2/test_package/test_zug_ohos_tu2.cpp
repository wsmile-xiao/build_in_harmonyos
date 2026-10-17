// zug 鸿蒙专项测试（第 2 翻译单元）：把类型擦除的 transducer 与可复用管道
// 放在另一个 TU 里实例化，验证 OHOS clang15/libc++ 下跨翻译单元的模板
// 实例化、typeinfo/vtable 与状态复用行为。
#include <zug/compose.hpp>
#include <zug/into_vector.hpp>
#include <zug/transducer/filter.hpp>
#include <zug/transducer/map.hpp>
#include <zug/transducer/transducer.hpp>

#include <string>
#include <vector>

// 注意：zug::transducer 的 operator() 不是 const（meta.hpp 里擦除管道以非常量
// 可调用对象使用），跨 TU 传递必须用非常量引用，否则 into_vector 调用它编不过。
std::vector<std::string> zug_ohos_apply(zug::transducer<int, std::string> &xform,
                                        const std::vector<int> &in)
{
    return zug::into_vector(xform, in);
}

std::vector<int> zug_ohos_reused_pipeline(const std::vector<int> &in)
{
    static auto xform =
        zug::comp(zug::filter([](int x) { return x > 1; }),
                  zug::map([](int x) { return x * 2; }));
    auto first  = zug::into_vector(xform, in);
    auto second = zug::into_vector(xform, in);
    // 同一条管道连续两次转导必须给出同样结果：管道本身不得携带可变态。
    return first == second ? first : std::vector<int>{};
}
