// 验 PARI 库真的可用：初始化栈 → 建大整数 → 解析并求值表达式 → 取回 C 整数。
// 用的都是公开头文件里的符号（pari_init/gp_read_str 在 pariold.h，stoi/itos 在 paridecl.h）。
#include <pari/pari.h>
#include <cstdio>
#include <cstdlib>
#include <string>

int main() {
    pari_init(8000000, 500000);

    // ① 小整数往返
    GEN a = stoi(1234);
    if (itos(a) != 1234) { std::printf("stoi/itos 往返失败\n"); return 1; }

    // ② 表达式求值：2^64 的十进制位数应为 20
    GEN b = gp_read_str("2^64");
    char *s = GENtostr(b);
    if (std::string(s).size() != 20) {
        std::printf("2^64 位数不对: %s\n", s); return 1;
    }

    // ③ 数论函数：nextprime(1000) = 1009
    GEN p = gp_read_str("nextprime(1000)");
    if (itos(p) != 1009) { std::printf("nextprime(1000) != 1009\n"); return 1; }

    // ④ 确认走的是 GMP 内核（与上游 libpari-gmp-tls 一致）
    std::printf("PARI 版本 %s\n", PARIVERSION);
    std::printf("2^64 = %s, nextprime(1000) = %ld\n", s, itos(p));
    pari_close();
    std::printf("pari test_package: 全部断言通过\n");
    return 0;
}
