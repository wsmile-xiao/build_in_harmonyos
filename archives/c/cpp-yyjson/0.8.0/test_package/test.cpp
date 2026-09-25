// test_package consumer test — cpp-yyjson 0.8.0
// 消费者视角验证：仅通过已安装的公开头文件 cpp_yyjson.hpp 与公开 API
// 读取/写入 JSON，验证编译、链接与运行（R34：必须实际调用被测包 API）。
#include <iostream>
#include <string_view>

#include "cpp_yyjson.hpp"

int main()
{
    using namespace yyjson;

    // Reader: 解析 JSON 字符串并访问公开 API
    const char* json_str = R"({"id":1,"pi":3.141592,"name":"example","array":[0,1,2,3],"success":true})";
    auto val = read(json_str);
    auto obj = val.as_object();
    if (!obj) {
        std::cerr << "FAIL: as_object() failed" << std::endl;
        return 1;
    }
    auto id = (*obj)["id"].as_int();
    if (!id || *id != 1) {
        std::cerr << "FAIL: id != 1" << std::endl;
        return 1;
    }
    auto name = (*obj)["name"].as_string();
    if (!name || *name != "example") {
        std::cerr << "FAIL: name != example" << std::endl;
        return 1;
    }
    auto arr = (*obj)["array"].as_array();
    if (!arr || (*arr).size() != 4) {
        std::cerr << "FAIL: array size != 4" << std::endl;
        return 1;
    }

    // Writer: 构造 JSON 并序列化
    auto wobj = object();
    wobj.emplace("USD", 129.66);
    wobj.emplace("ok", true);
    auto out = wobj.write();
    if (out.empty()) {
        std::cerr << "FAIL: writer produced empty output" << std::endl;
        return 1;
    }
    std::cout << "cpp-yyjson 0.8.0 consumer test: OK -> " << out << std::endl;
    return 0;
}
