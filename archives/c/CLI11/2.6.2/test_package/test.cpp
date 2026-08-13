#include <CLI/CLI.hpp>
#include <string>
#include <iostream>

int main(int argc, char** argv) {
    CLI::App app{"CLI11 test program"};

    std::string filename;
    int count = 0;
    bool flag = false;

    app.add_option("-f,--file", filename, "Input file");
    app.add_option("-n,--count", count, "Count value");
    app.add_flag("--flag", flag, "Boolean flag");

    // 模拟命令行参数解析
    const char* test_argv[] = {"test_cli11", "-f", "input.txt", "-n", "42", "--flag"};
    int test_argc = sizeof(test_argv) / sizeof(test_argv[0]);

    CLI11_PARSE(app, test_argc, test_argv);

    // 验证解析结果
    if (filename != "input.txt") {
        std::cerr << "FAIL: filename expected 'input.txt', got '" << filename << "'" << std::endl;
        return 1;
    }
    if (count != 42) {
        std::cerr << "FAIL: count expected 42, got " << count << std::endl;
        return 1;
    }
    if (!flag) {
        std::cerr << "FAIL: flag expected true, got false" << std::endl;
        return 1;
    }

    std::cout << "CLI11 test PASSED: file=" << filename
              << ", count=" << count
              << ", flag=" << (flag ? "true" : "false") << std::endl;
    return 0;
}
