// test_openddl_parser.cpp — openddl-parser 0.5.2 消费者验证（test_package）
//
// 仅通过库已安装/导出的公开头文件 openddlparser/OpenDDLParser.h、
// openddlparser/DDLNode.h、openddlparser/Value.h 与公开 API 使用本库：
// 构造 OpenDDL 文本 -> parse() -> getRoot() 遍历子节点 -> 校验可观察结果，
// 验证第三方使用者能编译、链接、调用并正常运行本库。
// 不包含库私有头文件、不调用内部符号。
#include <openddlparser/OpenDDLParser.h>
#include <openddlparser/DDLNode.h>
#include <openddlparser/Value.h>

#include <cstdio>
#include <cstring>
#include <string>

using namespace ODDLParser;

int main() {
    // OpenDDL 结构：三个 Metric 结构（上游集成测试 parseMetricTest 同款语法）
    const char *ddl =
        "Metric( key = \"distance\" ) { float{ 1.5 } }\n"
        "Metric( key = \"up\" ) { float{ 2.5 } }\n"
        "Metric( key = \"time\" ) { float{ 3.5 } }\n";

    OpenDDLParser parser(ddl, std::strlen(ddl));
    if (!parser.parse()) {
        std::printf("CONSUMER_FAIL: parse() returned false\n");
        return 1;
    }

    DDLNode *root = parser.getRoot();
    if (root == nullptr) {
        std::printf("CONSUMER_FAIL: getRoot() returned null\n");
        return 1;
    }

    // 统计根节点直下子节点数，验证可观察解析结果
    const DDLNode::DllNodeList &children = root->getChildNodeList();
    std::printf("parsed root child count = %zu\n", children.size());
    if (children.size() != 3) {
        std::printf("CONSUMER_FAIL: expected 3 children, got %zu\n", children.size());
        return 1;
    }

    // 校验第一个子节点类型名（getType() 返回 std::string）
    const std::string &typeName = children[0]->getType();
    std::printf("first child type = %s\n", typeName.c_str());
    if (typeName != "Metric") {
        std::printf("CONSUMER_FAIL: unexpected first child type '%s'\n", typeName.c_str());
        return 1;
    }

    // 通过公开 Property API 读取第一个节点的属性值（key = "distance"）
    Property *prop = children[0]->getProperties();
    if (prop == nullptr || prop->m_value == nullptr || prop->m_value->m_data == nullptr) {
        std::printf("CONSUMER_FAIL: first child has no property value\n");
        return 1;
    }
    std::printf("first child property value = %s\n", (const char *)prop->m_value->m_data);
    if (std::strncmp((const char *)prop->m_value->m_data, "distance", 8) != 0) {
        std::printf("CONSUMER_FAIL: unexpected property value\n");
        return 1;
    }

    // 公开版本查询 API（上游 v0.5.2 tag 内部 Version 字符串为 0.4.0，属上游事实）
    std::printf("openddl-parser version = %s\n", OpenDDLParser::getVersion());

    std::printf("CONSUMER_PASS: openddl-parser public API consumed OK\n");
    return 0;
}