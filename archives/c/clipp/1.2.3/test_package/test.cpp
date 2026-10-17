// test_package 消费者测试 — clipp 1.2.3
// 真实调用 clipp API：解析命令行参数并校验结果（R34 非空壳）。
#include <cstdio>
#include <cstdlib>
#include <string>
#include "clipp.h"

int main() {
    using namespace clipp;
    // 定义与 examples/naval_fate.cpp 相似的 CLI（数值选项用 option & value 惯用法）
    bool a = false, b = false;
    int n = 0;
    std::string name;
    auto cli = (
        option("-a").set(a)            % "activate a",
        option("-b").set(b)            % "activate b",
        (option("-n") & value("n", n)) % "number",
        value("name", name)            % "name of the thing"
    );

    // 与上游 parse(argc, argv, cli) 重载一致：char* argv[]，自动省略 argv[0]
    char* argv[] = {(char*)"prog", (char*)"-a", (char*)"-n", (char*)"42", (char*)"hello"};
    int argc = 5;

    if (!parse(argc, argv, cli)) {
        std::printf("test clipp 1.2.3: FAILED (parse returned false)\n");
        return 1;
    }
    if (!a || b || n != 42 || name != "hello") {
        std::printf("test clipp 1.2.3: FAILED (a=%d b=%d n=%d name=%s)\n",
                    (int)a, (int)b, n, name.c_str());
        return 1;
    }
    std::printf("test clipp 1.2.3: OK (a=1 n=42 name=hello)\n");
    return 0;
}