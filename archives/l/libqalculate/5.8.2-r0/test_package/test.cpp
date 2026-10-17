#include <stdio.h>
#include <string>
#include <libqalculate/qalculate.h>

int main(void) {
    // 实质测试：创建 Calculator 实例并执行算术表达式（R34：必须调用被测包 API）
    Calculator *calc = new Calculator();
    if (!calc) {
        fprintf(stderr, "FAIL: Failed to create Calculator instance\n");
        return 1;
    }
    // libqalculate 5.8.2: calculate(std::string) 按值返回 MathStructure
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