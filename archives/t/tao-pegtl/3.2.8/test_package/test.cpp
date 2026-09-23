#include <tao/pegtl.hpp>
#include <cstdlib>
#include <iostream>

namespace pegtl = TAO_PEGTL_NAMESPACE;

// 最小 PEG 文法：非空数字串 + 文件结尾
struct number : pegtl::plus<pegtl::digit> {};
struct grammar : pegtl::must<number, pegtl::eof> {};

int main() {
    // 有效输入：must<> 组合子应解析成功
    pegtl::string_input in("12345", "test_input");
    if (!pegtl::parse<grammar>(in)) {
        std::cerr << "FAIL: pegtl parse of valid number rejected\n";
        return 1;
    }

    // 无效输入：must<> 失败时抛 parse_error（而非返回 false）
    bool rejected = false;
    try {
        pegtl::string_input bad("12a5", "test_input");
        pegtl::parse<grammar>(bad);
    } catch (const pegtl::parse_error&) {
        rejected = true;
    }
    if (!rejected) {
        std::cerr << "FAIL: pegtl parse accepted invalid input\n";
        return 1;
    }

    std::cout << "tao-pegtl 3.2.8 test_package: parse OK\n";
    return 0;
}