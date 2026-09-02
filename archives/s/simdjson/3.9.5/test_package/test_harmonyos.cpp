// HarmonyOS 专项测试 — 验证 simdjson 在 OHOS (aarch64-linux-ohos) 平台实际消费入口
#include <simdjson.h>
#include <iostream>
#include <cassert>
#include <cstring>

int main(void) {
    // 1) ondemand parser 真实调用（消费入口）
    simdjson::ondemand::parser parser;
    const char* json_str = R"({"platform":"HarmonyOS","arch":"aarch64","ok":true})";
    simdjson::padded_string json(json_str, std::strlen(json_str));
    auto doc = parser.iterate(json);
    std::string_view platform = std::string_view(doc.at_pointer("/platform"));
    std::string_view arch = std::string_view(doc.at_pointer("/arch"));
    bool ok = bool(doc.at_pointer("/ok"));
    assert(platform == "HarmonyOS");
    assert(arch == "aarch64");
    assert(ok);
    std::cout << "harmonyos test passed: platform=" << platform
              << " arch=" << arch << " ok=" << ok << std::endl;

    // 2) DOM 解析器（另一消费入口，避免只测单一 API）
    simdjson::dom::parser dom_parser;
    const char* dom_json_str = R"({"count":42})";
    simdjson::padded_string dom_json(dom_json_str, std::strlen(dom_json_str));
    simdjson::dom::element elem = dom_parser.parse(dom_json);
    uint64_t count = uint64_t(elem["count"]);
    assert(count == 42);
    std::cout << "harmonyos dom test passed: count=" << count << std::endl;
    return 0;
}
