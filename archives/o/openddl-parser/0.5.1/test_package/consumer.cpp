/*-----------------------------------------------------------------------------------------------
 * openddl-parser 0.5.1 — test_package 消费者测试（鸿蒙特有测试）
 *
 * 目的：从“消费者”视角验证 conan 导出的包可被 find_package + 链接 + 运行，
 *       并通过公开 API 完成真实解析（不是打印型空壳测试）。
 * 计数：每个 check() 是一条消费者断言，全部计入「鸿蒙特有测试」行（不进上游分母）。
 *-----------------------------------------------------------------------------------------------*/
#include <openddlparser/DDLNode.h>
#include <openddlparser/OpenDDLCommon.h>
#include <openddlparser/OpenDDLParser.h>

#include <cstdio>
#include <cstring>
#include <string>

USE_ODDLPARSER_NS

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char *what) {
    ++g_checks;
    if (ok) {
        std::printf("[ OK ] %s\n", what);
    } else {
        ++g_failed;
        std::printf("[FAIL] %s\n", what);
    }
}

int main() {
    // C1: 版本查询接口可链接且返回非空串（上游该串由 code/OpenDDLParser.cpp 维护）
    const char *ver = OpenDDLParser::getVersion();
    check(nullptr != ver && std::strlen(ver) > 0, "getVersion() 返回非空版本串");
    std::printf("       getVersion() = \"%s\"\n", ver ? ver : "(null)");

    // C2: 解析两段合法 OpenDDL 文本
    char token[] = "Metric( key = \"distance\" ) { float{ 1 } }\n"
                   "Metric( key = \"up\" ) { float{ 1 } }\n";
    OpenDDLParser parser;
    parser.setBuffer(token, std::strlen(token));
    check(parser.parse(), "parse() 对合法输入返回 true");

    // C3: 解析结果产生根节点
    DDLNode *root = parser.getRoot();
    check(nullptr != root, "getRoot() 非空");
    if (nullptr != root) {
        const DDLNode::DllNodeList &childs = root->getChildNodeList();
        check(2 == childs.size(), "根节点子节点数 == 2");
        if (2 == childs.size()) {
            check(0 == childs[0]->getType().compare("Metric"), "第 1 个子节点 type == Metric");
            check(0 == childs[1]->getType().compare("Metric"), "第 2 个子节点 type == Metric");
            Property *prop = childs[0]->getProperties();
            check(nullptr != prop && nullptr != prop->m_value, "子节点属性 Property 可读");
        }
    }

    // C4/C5: 垃圾输入必须被拒绝（解析器健壮性，实测 parse/validate 双 false）
    char junk[] = "@@@ ###";
    OpenDDLParser badParser;
    badParser.setBuffer(junk, std::strlen(junk));
    check(!badParser.parse(), "parse() 对垃圾输入返回 false");
    OpenDDLParser valParser;
    valParser.setBuffer(junk, std::strlen(junk));
    check(!valParser.validate(), "validate() 对垃圾输入返回 false");

    std::printf("SUMMARY checks=%d passed=%d failed=%d\n",
                g_checks, g_checks - g_failed, g_failed);
    return 0 == g_failed ? 0 : 1;
}
