// xsimd 14.2.0 真实功能测试（R34 反空壳）：实例化 batch、真做向量运算、断言数值。
#include <xsimd/xsimd.hpp>
#include <cstdint>
#include <cstdio>

static int failures = 0;
#define CHECK(cond, what)                                            \
    do {                                                             \
        if (!(cond)) { std::printf("FAIL: %s\n", (what)); ++failures; } \
        else         { std::printf("ok  : %s\n", (what)); }             \
    } while (0)

int main() {
    using B = xsimd::batch<int32_t, xsimd::default_arch>;
    std::printf("xsimd batch<int32_t> 宽度 = %d\n", (int)B::size);
    CHECK(B::size > 0, "batch 宽度为正（模板真的实例化出来了）");
    B a(int32_t(1)), b(int32_t(2));
    int32_t out[B::size];
    (a + b).store_unaligned(out);
    bool all3 = true;
    for (int i = 0; i < (int)B::size; ++i) if (out[i] != 3) all3 = false;
    CHECK(all3, "向量加法 1+2 逐 lane 都等于 3");
    CHECK(xsimd::reduce_add(a * B(int32_t(5))) == 5 * (int) B::size,
          "乘法后按 lane 求和 == 5 * 宽度");
    using D = xsimd::batch<double, xsimd::default_arch>;
    double dout[D::size];
    (D(1.5) + D(2.5)).store_unaligned(dout);
    CHECK(dout[0] == 4.0, "double 特化：1.5+2.5 == 4.0");
    if (failures) { std::printf("xsimd: %d 项断言失败\n", failures); return 1; }
    std::printf("xsimd: 全部断言通过\n");
    return 0;
}
