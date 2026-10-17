// libgmpxx 6.3.0 test_package：GMP C++ 绑定的消费者视角验证。
// 断言全部比对真实计算结果；operator<< 的插入器实现位于 libgmpxx
// 的非内联翻译单元（cxx/os*.cc），缺 libgmpxx 链接时无法通过链接阶段。
#include <gmpxx.h>

#include <iostream>
#include <sstream>
#include <string>

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    if (!ok) {
        std::cout << "FAIL: " << what << std::endl;
        ++failures;
    }
}

}  // namespace

int main() {
    // mpz_class 大整数乘法：12345678901234567890^2
    mpz_class a("12345678901234567890");
    mpz_class square = a * a;
    check(square == mpz_class("152415787532388367501905199875019052100"),
          "mpz 12345678901234567890^2");

    // mpz 2^100 的十进制位数 == 31
    mpz_class pow2 = mpz_class(1) << 100;
    std::ostringstream digits;
    digits << pow2;
    check(digits.str().size() == 31, "2^100 decimal digit count == 31");

    // mpq_class 有理数：1/3 + 1/6 == 1/2
    mpq_class q = mpq_class(1, 3) + mpq_class(1, 6);
    q.canonicalize();
    check(q == mpq_class(1, 2), "mpq 1/3 + 1/6 == 1/2");

    // mpf_class 浮点：0.5 * 6 == 3
    mpf_class f("0.5");
    f = f * 6;
    check(mpf_cmp_ui(f.get_mpf_t(), 3) == 0, "mpf 0.5 * 6 == 3");

    // operator<< 经 libgmpxx 非内联插入器输出
    std::ostringstream out;
    out << mpz_class(4096);
    check(out.str() == "4096", "ostream prints mpz_class");

    if (failures != 0) {
        std::cout << failures << " assertion(s) failed" << std::endl;
        return 1;
    }
    std::cout << "libgmpxx test_package: all assertions passed" << std::endl;
    return 0;
}
