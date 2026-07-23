// test_crow.cpp — L1 smoke test for crow 1.3.3 header-only library
// 验证 crow 头文件可正常包含、SimpleApp 可实例化、路由定义和 JSON 功能正常
#include "crow.h"
#include <iostream>
#include <string>

int main() {
    // 测试 1: SimpleApp 实例化
    crow::SimpleApp app;

    // 测试 2: JSON 创建与序列化
    crow::json::wvalue json_obj;
    json_obj["name"] = "crow";
    json_obj["version"] = "1.3.3";
    json_obj["port"] = 8080;
    std::string json_str = json_obj.dump();
    if (json_str.find("crow") == std::string::npos) {
        std::cerr << "FAIL: JSON 序列化未包含预期字段" << std::endl;
        return 1;
    }

    // 测试 3: JSON 解析
    auto parsed = crow::json::load(R"({"key":"value","num":42})");
    if (!parsed) {
        std::cerr << "FAIL: JSON 解析失败" << std::endl;
        return 1;
    }
    std::string key_val = parsed["key"].s();
    if (key_val != "value") {
        std::cerr << "FAIL: JSON 解析字段值不匹配" << std::endl;
        return 1;
    }

    // 测试 4: 路由定义（不启动服务器）
    CROW_ROUTE(app, "/hello")([]() {
        return "Hello, Crow!";
    });

    std::cout << "PASS: crow header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
