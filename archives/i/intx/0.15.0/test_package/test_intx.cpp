// intx test_package — 消费者视角验证
// 使用 intx::intx 头文件库的公开 API 进行基本运算，验证安装后的 include 路径与链接
#include <intx/intx.hpp>

#include <cstdio>
#include <cstdint>

int main()
{
    // 构造 uint256 并做加法：0xffffffffffffffff + 1 = 2^64
    constexpr intx::uint256 a = 0xffffffffffffffffULL;
    constexpr intx::uint256 one = 1;
    constexpr intx::uint256 c = a + one;
    constexpr intx::uint256 big = intx::uint256{1} << 64;
    static_assert(c == big, "uint256 add failed");

    // 运行时验证
    intx::uint256 x = 10;
    intx::uint256 y = 20;
    intx::uint256 z = x * y;
    if (z != 200)
    {
        std::printf("FAIL: x*y = %s\n", intx::to_string(z).c_str());
        return 1;
    }
    if (x + y != 30)
    {
        std::printf("FAIL: x+y != 30\n");
        return 1;
    }

    std::printf("OK: intx consumer test passed (%s)\n", intx::to_string(z).c_str());
    return 0;
}
