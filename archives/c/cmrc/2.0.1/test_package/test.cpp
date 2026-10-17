#include <cmrc/cmrc.hpp>

#include <iostream>
#include <string>

// 命名空间须与 cmrc_add_resource_library 的 NAMESPACE 一致
CMRC_DECLARE(hello);

int main() {
    auto fs = cmrc::hello::get_filesystem();
    auto data = fs.open("hello.txt");
    std::string content(data.begin(), data.end());
    std::cout << "cmrc consumer test: " << content << '\n';
    // 断言嵌入内容与源文件一致 (Hello, world!\n)
    if (content == "Hello, world!\n") {
        return 0;
    }
    std::cerr << "FAIL: embedded resource mismatch\n";
    return 1;
}