// test_ohos — libmcfp 2.1.1 OHOS 专项测试程序（真实编译并运行）
//
// 目的：在真实鸿蒙 PC（aarch64, OHOS）上验证本库的 OHOS 特有适配点 ——
// OHOS libc++ 无浮点 std::from_chars 重载（float/double 被 delete），
// 上游 try_compile 失败后走 fast_float 路径（USE_FAST_FLOAT），
// charconv-fast_float.cpp 特化 ff_charconv<float/double> 被编译进 libmcfp.a。
// 本程序用安装后的公开头文件与静态库，实际解析浮点选项并验证数值。
//
// 退出码：0=通过；1=解析失败；2=数值断言失败。
#include <mcfp/mcfp.hpp>

#include <cmath>
#include <iostream>
#include <string>
#include <system_error>

int main()
{
    auto &config = mcfp::config::instance();

    config.init("usage: ohos_ff_test [options]",
                mcfp::make_option<double>("double,d", 1.0, "a double (fast_float path)"),
                mcfp::make_option<float>("float,f", 1.0f, "a float (fast_float path)"));

    // -d 3.14159 -f 2.5 : 浮点解析必须经过 fast_float（OHOS 无 std::from_chars 浮点）
    const char *const args[] = {"ohos_ff_test", "-d", "3.14159", "-f", "2.5"};
    std::error_code ec;
    config.parse(5, args, ec);
    if (ec) {
        std::cerr << "mcfp parse error: " << ec.message() << "\n";
        return 1;
    }

    const double d = config.get<double>("double");
    const float f = config.get<float>("float");

    // 精度断言（fast_float 独立于 libc 实现的解析结果）
    if (std::fabs(d - 3.14159) > 1e-6 || std::fabs(f - 2.5f) > 1e-5f) {
        std::cerr << "BAD float values from fast_float path: d=" << d
                  << " f=" << f << "\n";
        return 2;
    }

    std::cout << "OHOS mcfp fast_float test OK (d=" << d << ", f=" << f << ")\n";
    return 0;
}