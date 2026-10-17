// test.cpp — 消费者用例：模拟上层组件调用 cxxopts 公开 API
//
// 验证：
//   1. include/cxxopts.hpp 可包含（公开头）
//   2. 编译链接 cxxopts::cxxopts 成功（header-only）
//   3. 调用跑通：解析 -n/--name 选项并校验结果（真实功能验证）
#include <cxxopts.hpp>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    cxxopts::Options options("test_cxxopts", "consumer test");
    options.add_options()
        ("n,name", "Name", cxxopts::value<std::string>())
        ("h,help", "Print usage");

    auto result = options.parse(argc, argv);

    /* 断言 1：help 选项默认 false */
    if (result.count("help") != 0) {
        std::cerr << "FAIL: help should not be set\n";
        return 1;
    }

    /* 断言 2/3：解析 -n 选项且值正确（真实调用 parse + count + as） */
    std::string name = result["name"].as<std::string>();
    if (name != "harmonyos") {
        std::cerr << "FAIL: name='" << name << "', expected 'harmonyos'\n";
        return 1;
    }

    std::cout << "test_cxxopts: OK (parsed name=" << name << ")\n";
    return 0;
}
