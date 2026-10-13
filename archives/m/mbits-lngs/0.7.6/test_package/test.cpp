#include <cstdio>
#include <lngs/plurals.hpp>
#include "plural_rule.hpp"

// 消费者验证：仅通过库安装/导出的公开头文件 <lngs/plurals.hpp> 调用公开 API
// lngs::plurals::decode / eval，验证第三方组件可编译、链接、调用并得到可观察结果。
int main() {
    int failure_count = 0;
    // 标准英语复数规则: nplurals=2; plural=(n != 1);
    auto const rule = lngs::plurals::decode(mbits_lngs_english_plural_rule);
    if (!rule) {
        ++failure_count;
        std::fprintf(stderr, "FAIL: decode returned empty rule\n");
        std::fprintf(stderr, "check 1 (decode) failed; remaining 5 checks were not run.\n");
        std::fprintf(stderr, "Failure count: %d (decode returned empty)\n", failure_count);
        return 1;
    }
    if (rule.nplurals != 2) {
        std::fprintf(stderr, "FAIL: nplurals=%lld, expected 2\n",
                     static_cast<long long>(rule.nplurals));
        ++failure_count;
    }
    // 公开 API 的可观察结果: eval(n) 返回复数索引
    long long const singular = rule.eval(1);
    long long const plural_five = rule.eval(5);
    long long const plural_zero = rule.eval(0);
    long long const plural_two = rule.eval(2);
    if (singular != 0) {
        std::fprintf(stderr, "FAIL: eval(1)=%lld, expected 0 (singular)\n", singular);
        ++failure_count;
    }
    if (plural_five != 1) {
        std::fprintf(stderr, "FAIL: eval(5)=%lld, expected 1 (plural)\n", plural_five);
        ++failure_count;
    }
    if (plural_zero != 1) {
        std::fprintf(stderr, "FAIL: eval(0)=%lld, expected 1 (plural)\n", plural_zero);
        ++failure_count;
    }
    if (plural_two != 1) {
        std::fprintf(stderr, "FAIL: eval(2)=%lld, expected 1 (plural)\n", plural_two);
        ++failure_count;
    }
    if (failure_count != 0) {
        std::fprintf(stderr, "Failure count: %d (of 6 checks)\n", failure_count);
        return 1;
    }
    std::printf("mbits-lngs consumer: decode+eval ok (n=0 -> %lld, n=1 -> %lld, n=2 -> %lld, n=5 -> %lld)\n",
                plural_zero, singular, plural_two, plural_five);
    return 0;
}
