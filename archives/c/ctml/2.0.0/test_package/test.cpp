// test_package/test.cpp — ctml 2.0.0 消费者视角真实用例（鸿蒙特有测试行）
//
// 从「已安装的 ctml 包」（package() 交付的 include/ctml.hpp）出发，真实调用
// CTML::Node / CTML::Document 接口并逐条断言渲染结果（R34：非空壳、非 print-only）。
// 断言失败 → 打印 CTML-CONSUMER 行并以 rc=1 退出 → conan create 失败。
//
// 取数：本文件宏 CHECK_EQ/CHECK_TRUE 的调用次数 = 消费者断言数（见 MANIFEST.yml）。
#include <ctml.hpp>

#include <iostream>
#include <string>

static int g_checks = 0;
static int g_failures = 0;

static void report(const char* what, const std::string& got, const std::string& want) {
    ++g_failures;
    std::cerr << "[FAIL] " << what << "\n       got : " << got
              << "\n       want: " << want << "\n";
}

static void check_eq(const char* what, const std::string& got, const std::string& want) {
    ++g_checks;
    if (got != want) report(what, got, want);
}

static void check_true(const char* what, bool cond) {
    ++g_checks;
    if (!cond) report(what, cond ? "true" : "false", "true");
}

static void check_size(const char* what, size_t got, size_t want) {
    ++g_checks;
    if (got != want) report(what, std::to_string(got), std::to_string(want));
}

int main() {
    // ── 1. 节点构造（上游 construction 面）──────────────────────────────
    check_eq("blank element",
             CTML::Node("p").ToString(), "<p></p>");
    check_eq("element with content",
             CTML::Node("p", "Hello world!").ToString(), "<p>Hello world!</p>");
    check_eq("classes and id from selector",
             CTML::Node("p.class.test#test", "Hello world!").ToString(),
             "<p class=\"class test\" id=\"test\">Hello world!</p>");

    {
        CTML::Node nested("p.test div.nested section.selectors", "");
        check_eq("nested selector construction", nested.ToString(),
                 "<p class=\"test\"><div class=\"nested\"><section class=\"selectors\"></section></div></p>");
    }

    // ── 2. 类切换（上游 behavior 面）────────────────────────────────────
    {
        CTML::Node node("p.class");
        node.ToggleClass("paragraph");
        check_eq("toggle class adds", node.ToString(), "<p class=\"class paragraph\"></p>");
        node.ToggleClass("class");
        check_eq("toggle class removes", node.ToString(), "<p class=\"paragraph\"></p>");
    }

    // ── 3. 文本与子节点拼接 ─────────────────────────────────────────────
    {
        CTML::Node node("div");
        node.AppendText("Hello ")
            .AppendChild(CTML::Node("span", "Maxwell"))
            .AppendText(", welcome back!");
        check_eq("append text and child", node.ToString(),
                 "<div>Hello <span>Maxwell</span>, welcome back!</div>");
    }

    // ── 4. 选择器与按名取子节点 ─────────────────────────────────────────
    check_eq("selector generation",
             CTML::Node("p.class.names#identify").GetSelector(),
             "p.class.names#identify");
    {
        CTML::Node node("div");
        node.AppendChild(CTML::Node("section"))
            .AppendChild(CTML::Node("article"))
            .AppendChild(CTML::Node("nav"));
        check_eq("get child by name", node.GetChildByName("nav").Name(), "nav");
    }

    // ── 5. 无闭合标签（img 等 void 元素，属性顺序不作断言依据）──────────
    {
        CTML::Node node("img");
        node.SetAttribute("alt", "an image")
            .SetAttribute("src", "image.png")
            .UseClosingTag(false);
        const std::string out = node.ToString();
        check_true("void element output is one of both attribute orders",
                   out == "<img src=\"image.png\" alt=\"an image\">" ||
                   out == "<img alt=\"an image\" src=\"image.png\">");
        check_eq("attribute read back", node.GetAttribute("alt"), "an image");
    }

    // ── 6. 按索引删子节点 / 原地删除 ────────────────────────────────────
    {
        CTML::Node node("div");
        node.AppendChild(CTML::Node("p", "hello world!"))
            .AppendChild(CTML::Node("span", "this is a removal test"))
            .AppendChild(CTML::Node("a", "i should be removed"));
        node.RemoveChild(2);
        check_eq("remove child by index", node.ToString(),
                 "<div><p>hello world!</p><span>this is a removal test</span></div>");
    }
    {
        CTML::Node node("div");
        CTML::Node badNode("p.bad-one", "remove me!");
        node.AppendChild(CTML::Node("p.not-right#child", "hello world! don't remove me!"))
            .AppendChild(CTML::Node("p.nice-one", "don't remove me either!"))
            .AppendChild(badNode);
        badNode.Remove();
        check_eq("remove node in place", node.ToString(),
                 "<div><p class=\"not-right\" id=\"child\">hello world! don't remove me!</p>"
                 "<p class=\"nice-one\">don't remove me either!</p></div>");
    }

    // ── 7. 属性值 HTML 转义与空属性 ─────────────────────────────────────
    {
        CTML::Node node("p", "Hello world!");
        node.SetAttribute("title", "\"Hello world\"")
            .SetAttribute("onclick", "<onclick()>");
        const std::string out = node.ToString();
        check_true("attribute values are html-escaped",
                   out.find("title=\"&quot;Hello world&quot;\"") != std::string::npos &&
                   out.find("onclick=\"&lt;onclick()&gt;\"") != std::string::npos);
    }
    check_eq("blank attribute renders name only",
             CTML::Node("button", "Log in").SetAttribute("disabled", "").ToString(),
             "<button disabled>Log in</button>");

    // ── 8. Document：doctype + head/body ─────────────────────────────────
    {
        CTML::Document document;
        document.AppendNodeToHead(CTML::Node("title", "ctml"));
        document.AppendNodeToBody(CTML::Node("a"));

        const std::string flat = document.ToString();
        check_true("document starts with doctype",
                   flat.rfind("<!DOCTYPE html>", 0) == 0);
        check_true("document contains head and body",
                   flat.find("<head>") != std::string::npos &&
                   flat.find("<body>") != std::string::npos);
        check_true("head node rendered",
                   flat.find("<title>ctml</title>") != std::string::npos);
        check_true("body child rendered", flat.find("<a></a>") != std::string::npos);
    }

    // ── 9. Document 多行格式化（与上游 behavior_tests 同期望字符串）──────
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("a"));
        document.AppendNodeToBody(CTML::Node("div a"));
        document.AppendNodeToBody(CTML::Node("nav"));
        check_eq("multi line formatting",
                 document.ToString(CTML::ToStringOptions(CTML::StringFormatting::MULTIPLE_LINES)),
                 "<!DOCTYPE html>\n"
                 "<html>\n"
                 "    <head>\n"
                 "    </head>\n"
                 "    <body>\n"
                 "        <a>\n"
                 "        </a>\n"
                 "        <div>\n"
                 "            <a>\n"
                 "            </a>\n"
                 "        </div>\n"
                 "        <nav>\n"
                 "        </nav>\n"
                 "    </body>\n"
                 "</html>");
    }

    // ── 10. QuerySelector：递归、类、标签、id、属性操作符 ───────────────
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div.one div.two div.three"));
        document.AppendNodeToBody(CTML::Node("div.two div.one div.three"));
        document.AppendNodeToBody(CTML::Node("div.three div.two div.one"));
        document.AppendNodeToBody(CTML::Node("div.three div.one div.two"));
        document.AppendNodeToBody(CTML::Node("div.four div.five section.needle div.six"));
        document.AppendNodeToBody(CTML::Node("div.seven div.eight section.needle div.nine"));
        document.AppendNodeToBody(CTML::Node("section.needle section.needle div.ten div.eleven"));
        check_size("selector by class recurses", document.QuerySelector("div.one").size(), 4);
        check_size("selector by .needle recurses", document.QuerySelector(".needle").size(), 4);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div.one div.two div.three div.five[data-test=\"do not find\"]"));
        document.AppendNodeToBody(CTML::Node("div.four div.five[data-test=\"find\"] div.six"));
        check_size("selector with attribute value",
                   document.QuerySelector(".five[data-test=\"find\"]").size(), 1);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div span section article header"));
        document.AppendNodeToBody(CTML::Node("video audio section ul table"));
        check_size("selector by element name", document.QuerySelector("section").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div#one div#two div#three"));
        document.AppendNodeToBody(CTML::Node("div#two div#four div#five"));
        check_size("selector by id", document.QuerySelector("#two").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div[data-test=\"testneedletest\"] div[data-test=\"testtesttest\"] div[data-test=\"testtesttest\"]"));
        document.AppendNodeToBody(CTML::Node("div[data-test=\"testtesttest\"] div[data-test=\"no\"] div[data-test=\"testneedletest\"]"));
        check_size("attribute contains [*=]",
                   document.QuerySelector("[data-test*=\"needle\"]").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div[data-test=\"testcorrect\"] div[data-test=\"negativetest\"] div[data-test=\"negativetest\"]"));
        document.AppendNodeToBody(CTML::Node("div[data-test=\"negativetest\"] div[data-test=\"no\"] div[data-test=\"testcorrect\"]"));
        check_size("attribute starts with [^=]",
                   document.QuerySelector("[data-test^=\"test\"]").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div[data-test=\"testgood\"] div[data-test=\"testbad\"] div[data-test=\"testbad\"]"));
        document.AppendNodeToBody(CTML::Node("div[data-test=\"testbad\"] div[data-test=\"no\"] div[data-test=\"testgood\"]"));
        check_size("attribute ends with [$=]",
                   document.QuerySelector("[data-test$=\"good\"]").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div[data-test=\"test needle test\"] div[data-test=\"test test test\"] div[data-test=\"test test test\"]"));
        document.AppendNodeToBody(CTML::Node("div[data-test=\"test test test\"] div[data-test=\"negate\"] div[data-test=\"test needle test\"]"));
        check_size("attribute word match [~=]",
                   document.QuerySelector("[data-test~=\"needle\"]").size(), 2);
    }
    {
        CTML::Document document;
        document.AppendNodeToBody(CTML::Node("div[data-test=\"test\"] div[data-test=\"rest-test\"] div[data-test=\"test-hyphen\"]"));
        document.AppendNodeToBody(CTML::Node("div[data-test=\"rest-test-\"] div[data-test=\"rest-test\"] div[data-test=\"rest-test\"]"));
        check_size("attribute hyphen match [|=]",
                   document.QuerySelector("[data-test|=\"test\"]").size(), 2);
    }

    std::cout << "CTML-CONSUMER checks=" << g_checks
              << " failures=" << g_failures << std::endl;
    return g_failures == 0 ? 0 : 1;
}
