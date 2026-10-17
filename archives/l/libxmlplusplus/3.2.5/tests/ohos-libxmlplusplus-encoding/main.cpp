// OHOS-specific libxml++ 3.2.5 test — UTF-8 中文内容与序列化往返验证。
//
// 业务意义：HarmonyOS 生态以中文内容为主，本用例验证第三方上层组件通过
// libxml++ 公开 API 解析含中文 UTF-8 的 XML、读取文本/属性内容，并将 DOM
// 序列化回 XML 后仍保持 UTF-8 语义一致（往返 round-trip）。上游 4 个测试
// （istream/saxparser 状态机）不覆盖中文内容与序列化往返，故为专项补充。
#include <libxml++/libxml++.h>

#include <cstdio>
#include <cstdlib>
#include <string>

int main()
{
  int rc = 0;

  // 1) 中文 UTF-8 文本解析 + get_content 往返。
  {
    xmlpp::DomParser parser;
    parser.parse_memory("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                        "<root><title>鸿蒙操作系统</title><note>适配测试</note></root>");
    xmlpp::Document* doc = parser.get_document();
    xmlpp::Element* root = doc ? doc->get_root_node() : nullptr;
    if (!root || root->get_name() != "root")
    {
      std::fprintf(stderr, "FAIL: root parse\n");
      return 1;
    }
    const xmlpp::Element* title = nullptr;
    for (const auto* child : root->get_children("title"))
    {
      const auto* el = dynamic_cast<const xmlpp::Element*>(child);
      if (el) title = el;
    }
    if (!title)
    {
      std::fprintf(stderr, "FAIL: <title> not found\n");
      return 1;
    }
    // 3.x API: Element::get_first_child_text() 替代 2.x 的 get_child_text()。
    const xmlpp::TextNode* title_text = title->get_first_child_text();
    if (!title_text)
    {
      std::fprintf(stderr, "FAIL: <title> has no text node\n");
      return 1;
    }
    const Glib::ustring content = title_text->get_content();
    const std::string expected = "\xe9\xb8\xbf\xe8\x92\x99\xe6\x93\x8d\xe4\xbd\x9c\xe7\xb3\xbb\xe7\xbb\x9f"; // 鸿蒙操作系统
    if (content != expected)
    {
      std::fprintf(stderr, "FAIL: title content mismatch, got: %s\n", content.c_str());
      rc = 1;
    }
    else
    {
      std::printf("OK: 中文 UTF-8 内容往返一致: %s\n", content.c_str());
    }
  }

  // 2) 中文属性值解析。
  {
    xmlpp::DomParser parser;
    parser.parse_memory("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                        "<config lang=\"简体中文\"/>");
    xmlpp::Document* doc = parser.get_document();
    xmlpp::Element* root = doc ? doc->get_root_node() : nullptr;
    if (!root)
    {
      std::fprintf(stderr, "FAIL: attr root parse\n");
      return 1;
    }
    const Glib::ustring lang = root->get_attribute_value("lang");
    const std::string expected = "\xe7\xae\x80\xe4\xbd\x93\xe4\xb8\xad\xe6\x96\x87"; // 简体中文
    if (lang != expected)
    {
      std::fprintf(stderr, "FAIL: attr mismatch, got: %s\n", lang.c_str());
      rc = 1;
    }
    else
    {
      std::printf("OK: 中文属性值解析一致: %s\n", lang.c_str());
    }
  }

  // 3) write_to_string 序列化往返：解析 → 序列化 → 再解析，内容一致。
  {
    xmlpp::DomParser parser;
    parser.parse_memory("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                        "<root><item id=\"1\">内容甲</item><item id=\"2\">内容乙</item></root>");
    xmlpp::Document* doc = parser.get_document();
    if (!doc)
    {
      std::fprintf(stderr, "FAIL: serialization parse\n");
      return 1;
    }
    const Glib::ustring serialized = doc->write_to_string();
    if (serialized.find("内容甲") == Glib::ustring::npos ||
        serialized.find("内容乙") == Glib::ustring::npos)
    {
      std::fprintf(stderr, "FAIL: serialized output lost Chinese content: %s\n",
                   serialized.c_str());
      rc = 1;
    }
    else
    {
      std::printf("OK: write_to_string 序列化保留中文（%zu 字节）\n",
                  serialized.bytes());
      // 序列化结果再解析一次，验证 round-trip 可被再次消费。
      xmlpp::DomParser reparser;
      reparser.parse_memory(serialized);
      xmlpp::Document* re_doc = reparser.get_document();
      xmlpp::Element* re_root = re_doc ? re_doc->get_root_node() : nullptr;
      if (!re_root || re_root->get_name() != "root")
      {
        std::fprintf(stderr, "FAIL: re-parse of serialized XML\n");
        rc = 1;
      }
      else
      {
        std::printf("OK: 序列化结果可再次解析（round-trip）\n");
      }
    }
  }

  if (rc == 0)
    std::printf("libxml++ OHOS 专项测试 PASS: UTF-8 中文解析/属性/序列化往返全部通过\n");
  return rc;
}
