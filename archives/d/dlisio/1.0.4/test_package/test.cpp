// <cstdint> 必须在 dlisio 头**之前** —— 上游 types.h:140 用了 std::uint8_t 却
// 没有自己 include <cstdint>（头文件不自包含）。上游构建里恰好有别的 TU 先引入了
// 它才一直没暴露；单独 include 这个头就会 `no type named 'uint8_t' in namespace 'std'`。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlisio/dlis/types.h>

// 真实计算：DLIS 是**大端**格式，这些解析函数的字节序处理正是最容易在新平台
// 上出错的地方（dlisio 自己的 CMake 里就有 HOST_LITTLE_ENDIAN 分支）。
// 只验「能编能链」恰好漏掉这一层。
int main() {
    int bad = 0;

    const char sshort_in[] = { (char)0xFF };                 // -1
    int8_t i8 = 0;
    dlis_sshort(sshort_in, &i8);
    if (i8 != -1) { std::printf("FAIL sshort=%d\n", (int)i8); bad++; }

    const char unorm_in[] = { 0x01, 0x02 };                  // 大端 0x0102 = 258
    uint16_t u16 = 0;
    dlis_unorm(unorm_in, &u16);
    if (u16 != 258) { std::printf("FAIL unorm=%u（大端解析错？）\n", (unsigned)u16); bad++; }

    const char ulong_in[] = { 0x00, 0x00, 0x01, 0x00 };      // 大端 = 256
    uint32_t u32 = 0;
    dlis_ulong(ulong_in, &u32);
    if (u32 != 256u) { std::printf("FAIL ulong=%u\n", (unsigned)u32); bad++; }

    const char f_in[] = { 0x40, 0x49, 0x0F, (char)0xDB };    // IEEE754 大端 ≈ π
    float f = 0.0f;
    dlis_fsingl(f_in, &f);
    if (!(f > 3.14158f && f < 3.14160f)) { std::printf("FAIL fsingl=%f\n", (double)f); bad++; }

    // 年份基准：DLIS 存「距 1900 的偏移」，两个方向都要对得上
    if (dlis_year(0) != DLIS_YEAR_ZERO) { std::printf("FAIL year(0)=%d\n", dlis_year(0)); bad++; }
    if (dlis_yearo(DLIS_YEAR_ZERO + 25) != 25) { std::printf("FAIL yearo\n"); bad++; }

    // 变长标识串：先长度后内容
    const char ident_in[] = { 0x03, 'a', 'b', 'c' };
    int32_t len = 0; char out[8] = {0};
    dlis_ident(ident_in, &len, out);
    if (len != 3 || std::strncmp(out, "abc", 3) != 0) {
        std::printf("FAIL ident len=%d out=%s\n", (int)len, out); bad++;
    }

    if (bad == 0) std::printf("dlisio 1.0.4: 7 项断言全过（大端解析 + 年份基准 + 变长串）\n");
    return bad ? 1 : 0;
}
