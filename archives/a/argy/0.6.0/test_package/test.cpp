// test_package 消费者测试：模拟业务上层组件通过公开头文件 argy.hpp
// 使用 argy 0.6.0 的公开 API（CliParser::addInt/addString/addBool/parse/getInt...）
// 验证第三方使用者能否编译、链接并正确解析命令行参数（R34 实质调用）。
#include "argy.hpp"
#include <cstdio>
#include <string>

int main(int argc, char* argv[]) {
    Argy::CliParser cli(argc, argv);
    cli.addInt({"-c", "--count"}, "Number of items to process", 5);
    cli.addString({"-n", "--name"}, "User name", "anonymous");
    cli.addBool({"-v", "--verbose"}, "Enable verbose output");

    auto args = cli.parse();

    int count = args.getInt("count");
    std::string name = args.getString("name");
    bool verbose = args.getBool("verbose");

    // 校验解析结果：默认值 + 命令行覆盖值
    if (count != 5) {
        std::printf("FAIL: expected count=5, got %d\n", count);
        return 1;
    }
    if (name != "anonymous") {
        std::printf("FAIL: expected name=anonymous, got %s\n", name.c_str());
        return 1;
    }
    if (verbose) {
        std::printf("FAIL: expected verbose=false\n");
        return 1;
    }
    std::printf("argy consumer test OK (count=%d, name=%s)\n", count, name.c_str());
    return 0;
}
