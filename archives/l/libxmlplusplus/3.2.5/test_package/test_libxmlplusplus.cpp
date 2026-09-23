// test_libxmlplusplus.cpp — 消费者验证 libxml++ 3.0 API（R34 实质 API 测试）
//
// 模拟业务上层组件：仅通过 libxml++ 已安装/导出的公开头文件与公开 API
// （xmlpp::DomParser / xmlpp::Document / xmlpp::Element / Node::get_children）
// 编译、链接并正常运行，验证第三方使用者可解析、遍历 XML DOM。
#include <libxml++/libxml++.h>

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <string>

// 解析一段 XML，验证 root 节点名、属性值与子节点迭代。
static int check_memory_parse()
{
  xmlpp::DomParser parser;
  parser.parse_memory("<?xml version=\"1.0\"?><root attr=\"v1\"><child>text</child></root>");
  xmlpp::Document* doc = parser.get_document();
  if (!doc)
  {
    std::fprintf(stderr, "FAIL: no document after parse_memory\n");
    return 1;
  }
  xmlpp::Element* root = doc->get_root_node();
  if (!root)
  {
    std::fprintf(stderr, "FAIL: no root node\n");
    return 1;
  }
  const std::string root_name = root->get_name();
  if (root_name != "root")
  {
    std::fprintf(stderr, "FAIL: unexpected root name '%s'\n", root_name.c_str());
    return 1;
  }
  const Glib::ustring attr = root->get_attribute_value("attr");
  if (attr != "v1")
  {
    std::fprintf(stderr, "FAIL: unexpected attr value '%s'\n", attr.c_str());
    return 1;
  }
  // 子节点迭代（NodeList range-for）：至少包含 <child>。
  int child_elements = 0;
  for (const auto* child : root->get_children())
  {
    if (dynamic_cast<const xmlpp::Element*>(child))
      ++child_elements;
  }
  if (child_elements < 1)
  {
    std::fprintf(stderr, "FAIL: no child element found\n");
    return 1;
  }
  return 0;
}

// 写一个临时 XML 文件，验证 DomParser::parse_file 实际文件解析。
static int check_file_parse()
{
  const char* path = "test_libxmlplusplus_input.xml";
  FILE* f = std::fopen(path, "w");
  if (!f)
  {
    std::fprintf(stderr, "FAIL: cannot create input xml\n");
    return 1;
  }
  std::fputs("<?xml version=\"1.0\"?><book><title>OHOS</title></book>", f);
  std::fclose(f);

  xmlpp::DomParser parser;
  parser.parse_file(path);
  std::remove(path);
  xmlpp::Document* doc = parser.get_document();
  if (!doc)
  {
    std::fprintf(stderr, "FAIL: no document after parse_file\n");
    return 1;
  }
  xmlpp::Element* root = doc->get_root_node();
  if (!root || root->get_name() != "book")
  {
    std::fprintf(stderr, "FAIL: parse_file root mismatch\n");
    return 1;
  }
  return 0;
}

int main()
{
  int rc = 0;
  rc |= check_memory_parse();
  rc |= check_file_parse();
  if (rc == 0)
    std::printf("libxml++ 3.0 consumer OK: parse_memory + parse_file both pass\n");
  return rc;
}