// 消费者测试 1/3：真实调用 JAULA::Parser::parseStream 解析嵌套 JSON，
// 按类型下转型取公开 API 值，并断言 repr 序列化结果。
#include <jaula.h>
#include "jaula_test_check.h"

#include <memory>
#include <sstream>
#include <string>

int main()
{
  const char *doc =
    "{ \"name\": \"jaula\", \"ver\": 1, \"ratio\": 0.55, \"ok\": true,"
    "  \"nil\": null, \"list\": [ 10, 20, 30 ] }";

  std::istringstream in(doc);
  std::unique_ptr<JAULA::Value_Complex> root;
  try
  {
    root.reset(JAULA::Parser::parseStream(in));
  }
  catch (JAULA::Exception &e)
  {
    std::cerr << "unexpected parse failure: " << e << std::endl;
    return 1;
  }
  check(static_cast<bool>(root), "parseStream returns a value");
  if (!root)
    return 1;

  JAULA::Value_Object *obj = dynamic_cast<JAULA::Value_Object *>(root.get());
  check(obj != nullptr, "root document is a JSON object");
  if (!obj)
    return 1;
  check(obj->size() == 6, "object exposes 6 members");
  check(!obj->empty(), "object is not empty");

  JAULA::Value_Object::dataType const &m = obj->getData();

  JAULA::Value_String const *s = dynamic_cast<JAULA::Value_String const *>(m.at("name"));
  check(s != nullptr && s->getData() == "jaula", "\"name\" reads back as string jaula");

  JAULA::Value_Number_Int const *i =
    dynamic_cast<JAULA::Value_Number_Int const *>(m.at("ver"));
  check(i != nullptr && i->getData() == 1L, "\"ver\" reads back as integer 1");

  JAULA::Value_Number const *d =
    dynamic_cast<JAULA::Value_Number const *>(m.at("ratio"));
  check(d != nullptr && d->getData() > 0.54 && d->getData() < 0.56,
        "\"ratio\" reads back as double 0.55");

  JAULA::Value_Boolean const *b =
    dynamic_cast<JAULA::Value_Boolean const *>(m.at("ok"));
  check(b != nullptr && b->getData() == true, "\"ok\" reads back as boolean true");

  JAULA::Value_Null const *n = dynamic_cast<JAULA::Value_Null const *>(m.at("nil"));
  check(n != nullptr, "\"nil\" reads back as JSON null");

  JAULA::Value_Array const *a =
    dynamic_cast<JAULA::Value_Array const *>(m.at("list"));
  check(a != nullptr, "\"list\" reads back as an array");
  if (!a)
    return 1;
  check(a->size() == 3, "array holds 3 elements");

  std::ostringstream rep;
  rep << *a;
  check(rep.str() == "[ 10, 20, 30 ]", "array repr round-trips to \"[ 10, 20, 30 ]\"");

  std::ostringstream orep;
  orep << *obj;
  check(orep.str().find("\"name\" : \"jaula\"") != std::string::npos,
        "object repr serializes the string member");
  check(orep.str().compare(0, 2, "{ ") == 0, "object repr opens with \"{ \"");

  return finish("test_parse");
}
