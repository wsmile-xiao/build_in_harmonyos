// test_libxmlpp.cpp — libxml++ 2.42.3（OLD 2.6 API 线）消费者测试。
//
// 真实调用 2.6 API（区别于 5.x 新 API）：
//   * xmlpp::DomParser::parse_file(path)   —— 磁盘文件解析（2.6 无
//     Document::parse_file 静态工厂；Document 只能通过 Parser 获取）
//   * DomParser::get_document() / Document::get_root_node() -> Element*
//   * Node::get_name() / Element::get_attribute_value()
//   * Node::get_children()（返回 Node::NodeList = std::list<Node*>，range-for）
//   * DomParser::parse_memory()            —— 内存解析（2.6 用法）
// 任一断言失败返回非 0。Document 归 DomParser 所有，不得 delete。
#include <libxml++/libxml++.h>

#include <cstdio>
#include <fstream>
#include <string>

namespace {

bool check(bool condition, const char* what) {
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

bool verify_document(xmlpp::DomParser& parser, const char* what) {
  xmlpp::Document* doc = parser.get_document();
  if (!check(doc != nullptr, what)) return false;

  xmlpp::Element* root = doc->get_root_node();
  if (!check(root != nullptr, "get_root_node() returned null")) return false;
  if (!check(root->get_name() == "root", "root element name == \"root\""))
    return false;
  if (!check(root->get_attribute_value("id") == "ohos",
             "root attribute id == \"ohos\""))
    return false;

  // 2.6 API：get_children() 返回 Node::NodeList（std::list<Node*>）；range-for 可用。
  const xmlpp::Node::NodeList& children = root->get_children();
  bool found_child = false;
  for (const xmlpp::Node* node : children) {
    const xmlpp::Element* el = dynamic_cast<const xmlpp::Element*>(node);
    if (el && el->get_name() == "child" &&
        el->get_attribute_value("name") == "a") {
      found_child = true;
    }
  }
  return check(found_child, "found <child name=\"a\"> element");
}

}  // namespace

int main() {
  const std::string xml =
      "<?xml version=\"1.0\"?>\n"
      "<root id=\"ohos\"><child name=\"a\">hello</child></root>\n";
  const std::string path = "test_libxmlpp.xml";

  // 把文档写到磁盘，以便练习 DomParser::parse_file()。
  {
    std::ofstream out(path.c_str(), std::ios::out | std::ios::trunc);
    out << xml;
    out.close();
    if (!check(static_cast<bool>(std::ifstream(path.c_str())),
               "write test xml file")) {
      return 1;
    }
  }

  try {
    // 2.6 API：DomParser 解析磁盘文件。
    xmlpp::DomParser parser;
    parser.set_validate(false);
    parser.parse_file(path);
    if (!verify_document(parser, "DomParser::parse_file() document")) return 1;

    // 2.6 API 次级校验：DomParser::parse_memory。
    xmlpp::DomParser parser2;
    parser2.set_validate(false);
    parser2.parse_memory(xml);
    if (!verify_document(parser2, "DomParser::parse_memory() document")) return 1;
  } catch (const std::exception& ex) {
    std::fprintf(stderr, "FAIL: exception: %s\n", ex.what());
    return 1;
  }

  std::printf("libxml++ 2.42.3 OK: DomParser::parse_file + parse_memory verified\n");
  return 0;
}
