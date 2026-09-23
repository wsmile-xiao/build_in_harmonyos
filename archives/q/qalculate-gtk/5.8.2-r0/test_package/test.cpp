/* test_package/test.cpp — qalculate-gtk 5.8.2-r0
 *
 * qalculate-gtk 是 GTK3 GUI 应用（无头系统无法启动 GUI），但它的核心依赖
 * libqalculate（计算引擎）可在无头环境运行。本测试验证 qalculate-gtk 包
 * 正确传递 libqalculate 依赖链：include 其头文件 + 链接其库 + 实质执行
 * 算术计算（R34：调用被测包核心依赖的真实 API）。
 */
#include <stdio.h>
#include <string>
#include <libqalculate/qalculate.h>

int main(void) {
    Calculator *calc = new Calculator();
    if (!calc) {
        fprintf(stderr, "FAIL: Failed to create Calculator instance\n");
        return 1;
    }
    MathStructure result = calc->calculate("1 + 2 * 6");
    std::string printed = result.print();
    printf("OK: 1 + 2 * 6 = %s\n", printed.c_str());
    bool ok = (printed.find("13") != std::string::npos);
    delete calc;
    if (!ok) {
        fprintf(stderr, "FAIL: unexpected result: %s\n", printed.c_str());
        return 1;
    }
    return 0;
}