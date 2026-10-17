// consumer_openddl_parser.cpp — openddl-parser 0.5.2 消费者验证用例
//
// 模拟业务上层组件「OGEX 场景资源加载器」：仅通过库已安装/导出的公开头文件
// (openddlparser/OpenDDLParser.h, openddlparser/DDLNode.h, openddlparser/Value.h)、
// 公开 API（OpenDDLParser::parse / getRoot / DDLNode 遍历与类型查询 /
// Property 键读取 / Value 值读取）与正常链接目标（libopenddlparser.a）编译、
// 链接并运行。不包含库私有头文件、不调用内部符号、不复用库内部测试构建目录。
//
// 业务场景：解析一段 OpenDDL 场景描述（Metric 度量 + GeometryNode 几何节点），
// 遍历节点树并统计/校验可观察结果，模拟真实上层应用对解析产物的消费。
#include <openddlparser/OpenDDLParser.h>
#include <openddlparser/DDLNode.h>
#include <openddlparser/Value.h>

#include <cstdio>
#include <cstring>
#include <string>

using namespace ODDLParser;

int main() {
    // 一段小型 OpenDDL 场景：两个 Metric 度量 + 一个 GeometryNode 几何节点
    const char *scene =
        "Metric( key = \"distance\" ) { float{ 10.0 } }\n"
        "Metric( key = \"angle\" ) { float{ 45.0 } }\n"
        "GeometryNode $node1 { string { \"box\" } }\n";

    OpenDDLParser parser(scene, std::strlen(scene));
    if (!parser.parse()) {
        std::printf("CONSUMER_FAIL: OpenDDLParser::parse() returned false\n");
        return 1;
    }

    DDLNode *root = parser.getRoot();
    if (root == nullptr) {
        std::printf("CONSUMER_FAIL: getRoot() returned null\n");
        return 1;
    }

    // 遍历节点树：统计 Metric / GeometryNode 数量（有业务意义）
    const DDLNode::DllNodeList &children = root->getChildNodeList();
    size_t metrics = 0, geometryNodes = 0;
    for (DDLNode *child : children) {
        const std::string &type = child->getType();
        if (type == "Metric") ++metrics;
        else if (type == "GeometryNode") ++geometryNodes;
    }
    std::printf("scene stats: Metric=%zu GeometryNode=%zu\n", metrics, geometryNodes);

    if (metrics != 2 || geometryNodes != 1) {
        std::printf("CONSUMER_FAIL: unexpected node counts\n");
        return 1;
    }

    // 通过公开 Property API 读取第一个 Metric 的属性值并核对可观察结果
    Property *prop = children[0]->getProperties();
    if (prop == nullptr || prop->m_value == nullptr || prop->m_value->m_data == nullptr) {
        std::printf("CONSUMER_FAIL: first Metric has no property value\n");
        return 1;
    }
    std::printf("first Metric property value = %s\n", (const char *)prop->m_value->m_data);
    if (std::strncmp((const char *)prop->m_value->m_data, "distance", 8) != 0) {
        std::printf("CONSUMER_FAIL: unexpected first Metric property value\n");
        return 1;
    }

    // 公开版本查询 API
    std::printf("openddl-parser version string = %s\n", OpenDDLParser::getVersion());

    std::printf("CONSUMER_PASS: consumer_openddl_parser OK\n");
    return 0;
}