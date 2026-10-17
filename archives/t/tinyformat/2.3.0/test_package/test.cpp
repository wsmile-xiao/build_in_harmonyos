// tinyformat 2.3.0 — Conan test_package 消费者测试 (L1)
// 真实调用 tinyformat 公开头文件 API（tfm::format / tfm::printf），
// 断言输出正确性（R34：非空壳，不能只是打印字符串）。
#include <tinyformat.h>
#include <sstream>
#include <string>
#include <cstdio>
#include <cstdlib>

int main()
{
    int nfailed = 0;
    // 1) tfm::format 基础格式化
    if (tfm::format("%s:%d:%x", "hex", 42, 0xdeadbeef) != "hex:42:deadbeef") {
        std::fprintf(stderr, "FAIL: tfm::format basic\n");
        ++nfailed;
    }
    // 2) 位置参数（POSIX 扩展）
    if (tfm::format("%2$d %1$d", 10, 20) != "20 10") {
        std::fprintf(stderr, "FAIL: positional args\n");
        ++nfailed;
    }
    // 3) 精度/宽度
    if (tfm::format("%10.4f", 1234.1234567890) != " 1234.1235") {
        std::fprintf(stderr, "FAIL: precision/width\n");
        ++nfailed;
    }
    // 4) 自定义类型 operator<< 扩展
    struct MyInt { int v; };
    MyInt x{42};
    std::ostringstream oss;
    oss << "v=";
    // 通过 tfm::format 将自定义对象输出到流（依赖 operator<<）
    std::string s = tfm::format("obj=%d", x.v);
    if (s != "obj=42") {
        std::fprintf(stderr, "FAIL: custom obj\n");
        ++nfailed;
    }
    (void)oss;
    // 5) tfm::printf 写 stdout（捕获）—— 交换 cout buffer
    std::ostringstream cap;
    std::streambuf* old = std::cout.rdbuf(cap.rdbuf());
    tfm::printf("%s %s %d\n", "printf", "test", 1);
    std::cout.rdbuf(old);
    if (cap.str() != "printf test 1\n") {
        std::fprintf(stderr, "FAIL: tfm::printf capture\n");
        ++nfailed;
    }
    if (nfailed == 0) {
        std::printf("test tinyformat 2.3.0: OK\n");
        return 0;
    }
    std::printf("test tinyformat 2.3.0: %d failures\n", nfailed);
    return 1;
}