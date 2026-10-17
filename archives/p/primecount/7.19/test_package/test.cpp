// primecount test_package —— 真实计算 + 数值断言
//
// 断言依据（素数计数函数 π(x)，标准值）：
//   π(100)      = 25
//   π(10^6)     = 78498
//   π("1000")   = "168"   ← **字符串重载**
//
// 第三条是本包存在的理由：passagemath 的 primecountpy 绑定调的正是
// `primecount::pi(const std::string&)`，该重载在 primecount 8.0 已被移除，
// 故必须钉 7.x。这条断言若失败即说明选错了版本。

#include <stdint.h>
#include <stddef.h>
#include <primecount.hpp>
#include <cstdio>
#include <string>

int main() {
    int64_t p100 = primecount::pi((int64_t)100);
    std::printf("primecount: pi(100) = %lld（期望 25）\n", (long long)p100);
    if (p100 != 25) {
        std::fprintf(stderr, "primecount: FAIL —— pi(100) 期望 25，实得 %lld\n",
                     (long long)p100);
        return 1;
    }

    int64_t p1e6 = primecount::pi((int64_t)1000000);
    std::printf("primecount: pi(10^6) = %lld（期望 78498）\n", (long long)p1e6);
    if (p1e6 != 78498) {
        std::fprintf(stderr, "primecount: FAIL —— pi(10^6) 期望 78498，实得 %lld\n",
                     (long long)p1e6);
        return 1;
    }

    std::string s = primecount::pi(std::string("1000"));
    std::printf("primecount: pi(\"1000\") = \"%s\"（期望 \"168\"）\n", s.c_str());
    if (s != "168") {
        std::fprintf(stderr,
                     "primecount: FAIL —— 字符串重载 pi(\"1000\") 期望 \"168\"，"
                     "实得 \"%s\"\n", s.c_str());
        return 1;
    }

    std::printf("primecount: OK —— 含字符串重载在内的真实计算断言通过\n");
    return 0;
}
