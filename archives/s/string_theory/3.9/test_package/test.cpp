#include <iostream>
#include "string_theory/string"
#include "string_theory/format"

int main() {
    // 真实调用 string_theory API：构造、格式化、转换
    ST::string s1("Hello");
    ST::string s2 = ST::string::from_utf8("World");

    ST::string joined = s1 + ", " + s2 + "!";
    if (joined != "Hello, World!") {
        std::cerr << "string_theory 3.9 test FAILED: concat got '" << joined.c_str() << "'" << std::endl;
        return 1;
    }

    // 格式化 API
    ST::string fmt = ST::format("{} + {} = {}", 1, 2, 3);
    if (fmt != "1 + 2 = 3") {
        std::cerr << "string_theory 3.9 test FAILED: format got '" << fmt.c_str() << "'" << std::endl;
        return 1;
    }

    // 数值转换 API（带结果状态）
    ST::conversion_result res;
    int parsed = ST::string("314").to_int(res);
    if (!res.ok() || parsed != 314) {
        std::cerr << "string_theory 3.9 test FAILED: to_int" << std::endl;
        return 1;
    }

    // 大小写转换
    ST::string upper = ST::string("abc").to_upper();
    if (upper != "ABC") {
        std::cerr << "string_theory 3.9 test FAILED: to_upper got '" << upper.c_str() << "'" << std::endl;
        return 1;
    }

    std::cout << "test string_theory 3.9: OK (joined='" << joined.c_str() << "')" << std::endl;
    return 0;
}