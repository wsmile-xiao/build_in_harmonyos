// test_package/test.cpp — 消费者端到端用例（真实调用 platform.equality 公共 API）
//
// 目的：证明安装后的 platform.equality 头文件包，能被独立消费者工程
//       find_package() 找到、include 并以 C++20 编译链接运行。
//       不是纯断言，而是走完整调用链：
//         any 相等分派 -> 注册自定义比较器 -> range 逐元素比较 -> 未注册类型抛异常
#include <Platform.Equality.h>

#include <any>
#include <cstdio>
#include <span>
#include <string>
#include <vector>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        ++g_checks;                                                         \
        if (!(cond)) {                                                      \
            ++g_failed;                                                     \
            std::printf("FAIL: %s\n", (msg));                               \
        } else {                                                            \
            std::printf("ok  : %s\n", (msg));                               \
        }                                                                   \
    } while (0)

// 自定义类型：验证 RegisterEqualityComparer 的运行期分派路径
namespace
{
    struct ExactString
    {
        std::string value;
    };
}

int main()
{
    // 1. std::any 内建类型分派：同类型走注册表比较器
    {
        std::any a = 552;
        std::any b = 4919;
        CHECK(a != b, "std::any(int,int) 不同值 -> 不等");
    }

    // 2. 类型不同 -> 直接 false（不查注册表）
    {
        std::any a = 42;
        std::any b = 42.0f;
        CHECK(a != b, "std::any(int,float) 类型不同 -> 不等");
    }

    // 3. std::string 走注册表（Any.h 内建 EQUALITY_COMPARER(std::string)）
    {
        std::any a = std::string{"i love green stuff"};
        std::any b = std::string{"i love green stuff"};
        CHECK(a == b, "std::any(std::string) 等值 -> 相等");
    }

    // 4. any 与裸值混比（operator==(TAny, TOther) 的 any_cast 路径）
    {
        std::any a = 12;
        CHECK(a == 12, "std::any(int) 与裸 int 混比");
    }

    // 5. 未注册类型 -> 抛 std::runtime_error（Any.h 的错误路径）
    {
        std::vector<int> v1{1, 2, 3};
        std::vector<int> v2{1, 2, 3};
        bool threw = false;
        try
        {
            (void)(std::any(v1) == std::any(v2));
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }
        CHECK(threw, "未注册类型比较 -> 抛 runtime_error");
    }

    // 6. 运行期注册自定义比较器后即可比较
    {
        Platform::Equality::RegisterEqualityComparer<ExactString>(
            [](const ExactString& l, const ExactString& r)
            { return l.value == r.value; });
        std::any a = ExactString{"alpha"};
        std::any b = ExactString{"alpha"};
        CHECK(a == b, "注册自定义比较器后 any == any");
    }

    // 7. Range.h：std::equal_to<range> 逐元素比较（std::ranges::equal 路径）
    {
        std::vector<int> v1{1, 2, 3, 4, 5};
        std::vector<int> v2{1, 2, 3, 4, 5};
        std::vector<int> v3{5, 4, 3, 2, 1};
        CHECK(std::equal_to<std::span<int>>{}(std::span{v1}, std::span{v2}),
              "range 相等 -> equal_to 为真");
        CHECK(!std::equal_to<std::span<int>>{}(std::span{v1}, std::span{v3}),
              "range 不等 -> equal_to 为假");
    }

    // 8. 长度不同的 range -> false
    {
        std::vector<int> v1{1, 2, 3};
        std::vector<int> v2{1, 2};
        CHECK(!std::equal_to<std::span<int>>{}(std::span{v1}, std::span{v2}),
              "range 长度不同 -> equal_to 为假");
    }

    std::printf("\nchecked=%d failed=%d\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
