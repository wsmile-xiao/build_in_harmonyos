#include <stdint.h>
#include <stddef.h>
#include <tinyxml2.h>

#include <cstdio>
#include <cstring>
#include <string>

// tinyxml2 11.0.0 —— 真实解析/构造/序列化验证（非 dlopen 空壳）。
// 断言：
//   ① 解析一段带属性/嵌套/文本/CDATA/实体的 XML，逐项取值核对
//   ② 数值属性按类型取出（QueryIntAttribute / QueryDoubleAttribute）
//   ③ 构造一棵新树并序列化，再解析回来做往返一致性
//   ④ 错误路径：畸形 XML 必须报错且 ErrorStr() 可读
//   ⑤ 实体转义在往返中保真（&amp; &lt; 等）—— 这条最能暴露编译期字符集/宽字符配置错

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

using namespace tinyxml2;

static const char *kXml =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<robot name=\"pin-probe\" dof=\"7\">\n"
    "  <link name=\"base\" mass=\"1.25\"/>\n"
    "  <link name=\"tip\" mass=\"0.5\"/>\n"
    "  <note>a &amp; b &lt; c</note>\n"
    "  <blob><![CDATA[raw <not> parsed]]></blob>\n"
    "</robot>\n";

int main() {
  // ① 解析并逐项核对
  XMLDocument doc;
  CHECK(doc.Parse(kXml) == XML_SUCCESS, "解析合法 XML 成功");

  XMLElement *root = doc.RootElement();
  CHECK(root != nullptr && std::strcmp(root->Name(), "robot") == 0,
        "根元素名为 robot");

  if (root) {
    CHECK(std::strcmp(root->Attribute("name"), "pin-probe") == 0,
          "根属性 name 取值正确");

    // ② 类型化取属性
    int dof = -1;
    CHECK(root->QueryIntAttribute("dof", &dof) == XML_SUCCESS && dof == 7,
          "QueryIntAttribute 取到 dof=7");

    int nlinks = 0;
    double mass_sum = 0.0;
    for (XMLElement *e = root->FirstChildElement("link"); e;
         e = e->NextSiblingElement("link")) {
      ++nlinks;
      double m = 0.0;
      if (e->QueryDoubleAttribute("mass", &m) == XML_SUCCESS) mass_sum += m;
    }
    CHECK(nlinks == 2, "遍历到 2 个 <link>");
    CHECK(mass_sum > 1.7499 && mass_sum < 1.7501,
          "QueryDoubleAttribute 求和 = 1.75");

    // ⑤ 实体解码
    XMLElement *note = root->FirstChildElement("note");
    CHECK(note && note->GetText() && std::string(note->GetText()) == "a & b < c",
          "XML 实体 &amp;/&lt; 正确解码");

    // CDATA 原样保留
    XMLElement *blob = root->FirstChildElement("blob");
    CHECK(blob && blob->GetText() &&
              std::string(blob->GetText()) == "raw <not> parsed",
          "CDATA 段原样保留");
  }

  // ③ 构造 → 序列化 → 再解析（往返一致）
  {
    XMLDocument out;
    XMLElement *cfg = out.NewElement("cfg");
    cfg->SetAttribute("k", 42);
    cfg->SetAttribute("s", "x&y");
    XMLElement *child = out.NewElement("child");
    child->SetText("hello <world>");
    cfg->InsertEndChild(child);
    out.InsertFirstChild(cfg);

    XMLPrinter printer;
    out.Accept(&printer);
    const std::string text = printer.CStr();
    CHECK(text.find("&amp;") != std::string::npos,
          "序列化时 & 被转义为 &amp;");

    XMLDocument back;
    CHECK(back.Parse(text.c_str()) == XML_SUCCESS, "序列化结果可被解析回来");
    XMLElement *bcfg = back.RootElement();
    int k = 0;
    CHECK(bcfg && bcfg->QueryIntAttribute("k", &k) == XML_SUCCESS && k == 42,
          "往返后整型属性保真");
    CHECK(bcfg && std::string(bcfg->Attribute("s")) == "x&y",
          "往返后含 & 的字符串属性保真");
    XMLElement *bchild = bcfg ? bcfg->FirstChildElement("child") : nullptr;
    CHECK(bchild && bchild->GetText() &&
              std::string(bchild->GetText()) == "hello <world>",
          "往返后含 < > 的文本保真");
  }

  // ④ 错误路径
  {
    XMLDocument bad;
    XMLError err = bad.Parse("<a><b></a>");
    CHECK(err != XML_SUCCESS, "畸形 XML 被判为错误");
    CHECK(bad.ErrorStr() != nullptr && std::strlen(bad.ErrorStr()) > 0,
          "ErrorStr() 返回可读错误描述");
  }

  if (failures) {
    std::fprintf(stderr, "\ntinyxml2: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\ntinyxml2 11.0.0: 全部断言通过\n");
  return 0;
}
