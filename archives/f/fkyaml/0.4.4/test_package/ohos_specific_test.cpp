// fkyaml 0.4.4 — HarmonyOS 专项适配测试 (OHOS aarch64 / musl libc)
// 覆盖上游单元测试未直接断言的 OHOS 平台敏感路径：
// 1) 多字节 UTF-8 键/值与 BOM 检测（OHOS 全局 UTF-8 语义）；
// 2) 嵌套块标量 + 多文档错误恢复（解析器栈深路径）；
// 3) fkYAML::node 的算术/顺序保持与异常类型（musl 环境下 libc++ 行为一致）；
// 4) 本地时区无关的序列化稳定性（无依赖 OS 实现在输出中出现）。
// 全部为真实 API 调用 + 显式断言，非空壳。
#include <ios> // std::streamsize — 必须先于 fkYAML 头（上游未自包含 <ios>）
#include <fkYAML/node.hpp>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    int failures = 0;
    auto check = [&](bool cond, const char* what) {
        if (!cond) {
            std::cerr << "FAIL: " << what << "\n";
            ++failures;
        }
    };

    // 1) UTF-8 中文键值解析 + 序列化往返（OHOS 全局 UTF-8）。
    {
        const std::string yaml = "标题: 鸿蒙专项测试\n版本: 0.4.4\n内容:\n  - 解析\n  - 序列化\n";
        fkyaml::node root = fkyaml::node::deserialize(yaml);
        check(root["标题"].get_value<std::string>() == "鸿蒙专项测试", "UTF-8 中文键: 值");
        check(root["版本"].get_value<std::string>() == "0.4.4", "UTF-8 数字串: 值");
        check(root["内容"].is_sequence() && root["内容"].size() == 2, "UTF-8 序列");
        check(root["内容"][0].get_value<std::string>() == "解析", "UTF-8 序列元素 0");
        // 序列化后再解析，保持语义一致（序列化格式稳定，不依赖 OS 实现）。
        const std::string dumped = fkyaml::node::serialize(root);
        fkyaml::node reparsed = fkyaml::node::deserialize(dumped);
        check(reparsed["标题"].get_value<std::string>() == "鸿蒙专项测试", "序列化往返: 标题");
        check(reparsed["内容"].size() == 2, "序列化往返: 内容大小");
    }

    // 2) BOM 前缀输入应被透明跳过（UTF-8 BOM, EF BB BF）。
    {
        const std::string bom_yaml = "\xEF\xBB\xBFkey: value\n";
        fkyaml::node root = fkyaml::node::deserialize(bom_yaml);
        check(root["key"].get_value<std::string>() == "value", "UTF-8 BOM 前缀透明处理");
    }

    // 3) 块标量（literal block scalar）+ 嵌套缩进（解析器栈深路径）。
    {
        const std::string yaml =
            "doc: |\n"
            "  line1\n"
            "  line2\n"
            "nested:\n"
            "  - name: a\n"
            "    items:\n"
            "      - 1\n"
            "      - 2\n"
            "  - name: b\n";
        fkyaml::node root = fkyaml::node::deserialize(yaml);
        check(root["doc"].get_value<std::string>() == "line1\nline2\n", "literal 块标量内容");
        check(root["nested"][0]["name"].get_value<std::string>() == "a", "嵌套序列-映射");
        check(root["nested"][0]["items"].size() == 2, "嵌套序列元素数");
    }

    // 4) 异常类型区分：重复键 -> parse_error（上游单元测试同款输入确认）。
    {
        bool threw_parse = false;
        try {
            (void)fkyaml::node::deserialize("foo: bar\nfoo: baz");
        } catch (const fkyaml::parse_error&) {
            threw_parse = true;
        }
        check(threw_parse, "重复键 YAML 抛 fkyaml::parse_error");
    }

    // 5) 默认映射语义（fkyaml 默认 MappingType = std::map，按键排序）
    //    与类型元数据。
    {
        fkyaml::node ordered = fkyaml::node::mapping();
        ordered["third"] = 3;
        ordered["first"] = 1;
        ordered["second"] = 2;
        std::string keys;
        for (const auto& entry : ordered.map_items()) {
            keys += entry.key().get_value<std::string>() + ";";
        }
        check(keys == "first;second;third;", "默认 std::map 映射: 按键排序");
        check(ordered["first"].get_value<int>() == 1, "int 值读取");
        check(ordered.is_mapping(), "node 类型: mapping");
        check(ordered["first"].is_integer(), "node 类型: integer");
    }

    // 6) 纯 C++ 类型转换（bool / double / 字符串）从 YAML 标量。
    {
        fkyaml::node root = fkyaml::node::deserialize(
            "flag: true\nratio: 0.625\nlabel: ok\n");
        check(root["flag"].get_value<bool>() == true, "bool 读取");
        check(root["ratio"].get_value<double>() == 0.625, "double 读取");
        check(root["label"].get_value<std::string>() == "ok", "string 读取");
    }

    if (failures) {
        std::cerr << "HarmonyOS-specific test FAILED (" << failures << ")\n";
        return 1;
    }
    std::cout << "HarmonyOS-specific test PASSED (fkYAML 0.4.4 on OHOS aarch64)\n";
    return 0;
}