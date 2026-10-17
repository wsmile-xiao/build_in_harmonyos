// 消费者测试 2/3：跑上游自带的真实 JSON 语料（examples/example1.json 与
// example3.json 压平缩进后的等价内容内嵌），并验证编程式构造 API（addItem/insertItem/getData）。
#include <jaula.h>
#include "jaula_test_check.h"

#include <memory>
#include <sstream>
#include <string>

int main()
{
  // ---- 上游 examples/example1.json（上游本就是单行文件）逐字原文 ----
  const char *ex1 = "[ 100, 500, 300, 200, 400 ]";
  std::istringstream in1(ex1);
  std::unique_ptr<JAULA::Value_Complex> r1;
  try
  {
    r1.reset(JAULA::Parser::parseStream(in1));
  }
  catch (JAULA::Exception &e)
  {
    std::cerr << "example1.json failed to parse: " << e << std::endl;
    return 1;
  }
  JAULA::Value_Array *a1 = dynamic_cast<JAULA::Value_Array *>(r1.get());
  check(a1 != nullptr, "example1.json parses to an array");
  if (!a1)
    return 1;
  check(a1->size() == 5, "example1.json has 5 elements");

  std::ostringstream rep1;
  rep1 << *a1;
  check(rep1.str() == "[ 100, 500, 300, 200, 400 ]",
        "example1.json repr round-trips exactly");

  std::list<JAULA::Value *> const &items = a1->getData();
  JAULA::Value_Number_Int const *first =
    dynamic_cast<JAULA::Value_Number_Int const *>(items.front());
  check(first != nullptr && first->getData() == 100L,
        "first element of example1.json is integer 100");

  // ---- 上游 examples/example3.json（上游为 30 行 Tab 缩进对象数组，此处压平为等价单行）----
  const char *ex3 =
    "[ { \"color\": \"red\", \"value\": \"#f00\" },"
    "  { \"color\": \"green\", \"value\": \"#0f0\" },"
    "  { \"color\": \"blue\", \"value\": \"#00f\" },"
    "  { \"color\": \"cyan\", \"value\": \"#0ff\" },"
    "  { \"color\": \"magenta\", \"value\": \"#f0f\" },"
    "  { \"color\": \"yellow\", \"value\": \"#ff0\" },"
    "  { \"color\": \"black\", \"value\": \"#000\" } ]";
  std::istringstream in3(ex3);
  std::unique_ptr<JAULA::Value_Complex> r3;
  try
  {
    r3.reset(JAULA::Parser::parseStream(in3));
  }
  catch (JAULA::Exception &e)
  {
    std::cerr << "example3.json failed to parse: " << e << std::endl;
    return 1;
  }
  JAULA::Value_Array *a3 = dynamic_cast<JAULA::Value_Array *>(r3.get());
  check(a3 != nullptr && a3->size() == 7, "example3.json parses to 7 objects");
  if (!a3)
    return 1;

  JAULA::Value_Object const *o0 =
    dynamic_cast<JAULA::Value_Object const *>(a3->getData().front());
  check(o0 != nullptr && o0->size() == 2, "first entry is a 2-member object");
  if (!o0)
    return 1;
  JAULA::Value_String const *color =
    dynamic_cast<JAULA::Value_String const *>(o0->getData().at("color"));
  check(color != nullptr && color->getData() == "red",
        "first entry color member equals \"red\"");

  // ---- 编程式构造：不解析，直接用公开容器 API ----
  JAULA::Value_Array built;
  built.addItem(JAULA::Value_Number_Int(7));
  built.addItem(JAULA::Value_Boolean(true));
  check(built.size() == 2, "addItem grows the array to 2 elements");
  std::ostringstream brep;
  brep << built;
  check(brep.str() == "[ 7, true ]", "built array repr equals \"[ 7, true ]\"");

  JAULA::Value_Object obj;
  obj.insertItem("greeting", JAULA::Value_String("hi jaula"));
  check(obj.size() == 1, "insertItem adds one object member");
  JAULA::Value_String const *g =
    dynamic_cast<JAULA::Value_String const *>(obj.getData().at("greeting"));
  check(g != nullptr && g->getData() == "hi jaula",
        "inserted value is retrievable through getData()");

  return finish("test_corpus");
}
