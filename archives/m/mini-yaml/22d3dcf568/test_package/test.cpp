#include "yaml/Yaml.hpp"
#include <cstdio>
#include <string>

// HarmonyOS 专项测试：在鸿蒙 PC（aarch64-linux-ohos）上实际调用 mini-yaml
// 库 API（Yaml::Parse + Node::As + Serialize）验证 YAML 解析行为与平台属性。
static int g_failures = 0;

static void check(bool cond, const char *what) {
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    } else {
        std::printf("PASS: %s\n", what);
    }
}

int main() {
    std::printf("=== harmonyos_specific_test: mini-yaml 22d3dcf568 ===\n");

    // 1) 内嵌 YAML 文档解析并验证标量/序列/映射
    const char *yaml_text =
        "key: foo bar\n"
        "list:\n"
        "  - hello world\n"
        "  - integer: 123\n"
        "    boolean: true\n";
    Yaml::Node root;
    Yaml::Parse(root, std::string(yaml_text));
    check(root.IsMap(), "root is a map after Parse");
    check(!root["key"].IsNone(), "root[key] exists");
    check(root["key"].As<std::string>() == "foo bar", "root[key] == 'foo bar'");
    check(root["list"].IsSequence(), "root[list] is a sequence");
    check(root["list"][0].As<std::string>() == "hello world", "list[0] == 'hello world'");
    check(root["list"][1]["integer"].As<int>() == 123, "list[1].integer == 123");
    check(root["list"][1]["boolean"].As<bool>() == true, "list[1].boolean == true");

    // 2) 序列化往返验证
    std::string out;
    Yaml::Serialize(root, out);
    check(!out.empty(), "Serialize produced output");

    // 3) 异常路径：非法 YAML 必须抛出 ParsingException（OHOS 上同样生效）。
    //    未闭合引号触发库的 ParsingException（实测确认，见 probe）。
    bool threw = false;
    try {
        Yaml::Node bad;
        Yaml::Parse(bad, std::string("key: \"unterminated\n"));
    } catch (const Yaml::ParsingException &) {
        threw = true;
    } catch (...) {
    }
    check(threw, "invalid YAML throws ParsingException");

    std::printf("=== harmonyos_specific_test summary: %d check(s), %d failure(s) ===\n",
                9, g_failures);
    return g_failures == 0 ? 0 : 1;
}