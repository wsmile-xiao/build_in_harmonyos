// 鸿蒙（OHOS）消费者用例 —— 真实调用 LiDIA 库做计算数论运算并断言结果。
//
// 本用例是「消费者用例」而非上游测试：验证打好的 lidia 包在 OHOS/aarch64 上
// 能否被第三方程序 include 头文件、链接静态库并正确执行运算。
//
// 说明：上游 LiDIA 自身**没有**自动化测试（全树 Makefile.am 无 TESTS/check_PROGRAMS，
// 实测 0 命中；test_roots_appl.cc 仅存在于 EXTRA_DIST 未进构建），故本用例
// 不替代上游测试统计，仅作为 OHOS 平台可行性验证。
//
// 头文件为 C++98 时代产物，故以 gnu++98 编译（与库本体一致，避免 ABI/语法差异）。
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

#include <LiDIA/bigint.h>
#include <LiDIA/LiDIA.h>

using namespace LiDIA;

static int failures = 0;
static int checks = 0;

static void check(const char *name, bool ok, const std::string &detail)
{
    checks++;
    if (ok) {
        std::cout << "ok: " << name;
        if (!detail.empty())
            std::cout << "  [" << detail << "]";
        std::cout << std::endl;
    } else {
        failures++;
        std::cout << "FAIL: " << name;
        if (!detail.empty())
            std::cout << "  [" << detail << "]";
        std::cout << std::endl;
    }
}

int main()
{
    // ① bigint 基本构造 + 十进制输出
    bigint a(123456789L);
    std::string s;
    {
        // LiDIA 的 bigint 提供 operator long / 输出到 ostream
        std::ostringstream oss;
        oss << a;
        s = oss.str();
    }
    check("bigint 构造与输出", s == "123456789", s);

    // ② gcd —— 计算数论最基础的能力，直接走 GMP 后端
    bigint x(48), y(18);
    bigint g = gcd(x, y);
    std::ostringstream oss_g;
    oss_g << g;
    check("gcd(48,18) == 6", oss_g.str() == "6", oss_g.str());

    // ③ lcm
    bigint l = lcm(bigint(4), bigint(6));
    std::ostringstream oss_l;
    oss_l << l;
    check("lcm(4,6) == 12", oss_l.str() == "12", oss_l.str());

    // ④ 大整数乘法（超出 64 位，验证 GMP 多精度后端真正工作）
    bigint big1(1000000000L);   // 1e9
    bigint big2(1000000000L);   // 1e9
    bigint prod = big1 * big2;  // 1e18
    std::ostringstream oss_p;
    oss_p << prod;
    check("1e9 * 1e9 == 1e18", oss_p.str() == "1000000000000000000", oss_p.str());

    // ⑤ 阶乘 30!（验证多精度累乘与比较）
    bigint fact(1);
    for (int i = 2; i <= 30; ++i)
        fact = fact * bigint(static_cast<long>(i));
    std::ostringstream oss_f;
    oss_f << fact;
    // 30! = 265252859812191058636308480000000
    check("30! 精确值", oss_f.str() == "265252859812191058636308480000000", oss_f.str());

    // ⑥ 素性检测（Miller-Rabin，k=10）
    bigint p17(17);
    check("is_prime(17) == true", p17.is_prime(10) == true, "17");
    bigint c21(21);
    check("is_prime(21) == false", c21.is_prime(10) == false, "21");

    // ⑦ 整数平方根
    bigint root;
    sqrt(root, bigint(100));
    std::ostringstream oss_s;
    oss_s << root;
    check("isqrt(100) == 10", oss_s.str() == "10", oss_s.str());

    // ⑧ 加法/减法与比较运算符
    bigint s1(100), s2(23);
    std::ostringstream oss_ad;
    oss_ad << (s1 + s2);
    std::ostringstream oss_sb;
    oss_sb << (s1 - s2);
    check("100 + 23 == 123", oss_ad.str() == "123", oss_ad.str());
    check("100 - 23 == 77", oss_sb.str() == "77", oss_sb.str());

    std::cout << std::endl;
    std::cout << "consumer checks=" << checks << " failures=" << failures << std::endl;
    if (failures != 0) {
        std::cout << "RESULT: FAILED (" << failures << " check(s) FAILED)" << std::endl;
        return 1;
    }
    std::cout << "RESULT: PASSED" << std::endl;
    return 0;
}
