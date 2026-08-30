#include <utf8.h>
#include <string>
#include <vector>
#include <iostream>

int main() {
    // UTF-8 -> UTF-32 解码
    std::string utf8 = "\xe4\xbd\xa0\xe5\xa5\xbd";  // "你好"
    std::vector<unsigned int> utf32;
    utf8::utf8to32(utf8.begin(), utf8.end(), std::back_inserter(utf32));
    if (utf32.size() != 2 || utf32[0] != 0x4F60 || utf32[1] != 0x597D) {
        std::cerr << "FAIL: utf8to32 decode" << std::endl;
        return 1;
    }
    // UTF-8 -> UTF-16 编码
    std::vector<unsigned short> utf16;
    utf8::utf8to16(utf8.begin(), utf8.end(), std::back_inserter(utf16));
    if (utf16.size() != 2 || utf16[0] != 0x4F60 || utf16[1] != 0x597D) {
        std::cerr << "FAIL: utf8to16 encode" << std::endl;
        return 1;
    }
    // 校验合法 UTF-8
    if (!utf8::is_valid(utf8.begin(), utf8.end())) {
        std::cerr << "FAIL: is_valid on valid UTF-8" << std::endl;
        return 1;
    }
    std::cout << "utfcpp test PASSED: utf8to32/utf8to16/is_valid OK" << std::endl;
    return 0;
}
