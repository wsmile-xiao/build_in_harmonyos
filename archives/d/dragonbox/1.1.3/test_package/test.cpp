// test_package/test.cpp — dragonbox 消费者测试
// 验证可包含 dragonbox.h 并做浮点转十进制（核心 header-only 算法）。
#include <dragonbox/dragonbox.h>
#include <cstdio>

int main() {
    // to_decimal：float → decimal_fp{significand, exponent}（header-only 核心算法）
    auto r = jkj::dragonbox::to_decimal(3.141592653589793);
    if (r.significand == 0 && r.exponent == 0) {
        fprintf(stderr, "FAIL: to_decimal returned zero\n");
        return 1;
    }

    printf("dragonbox smoke test: PASS (sig=%llu exp=%d)\n",
           static_cast<unsigned long long>(r.significand), r.exponent);
    return 0;
}
