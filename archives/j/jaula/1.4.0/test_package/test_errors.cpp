// 消费者测试 3/3：负例断言。上游 examples/malformed_example3.json 是官方自带的
// 非法语料（键名未加引号），必须被词法/语法分析器拒绝；另外两条断言覆盖
// 类型收窄与重名键的异常码。断言依据是异常对象的 getCode()，不是"有没有抛"。
#include <jaula.h>
#include "jaula_test_check.h"

#include <sstream>
#include <string>

int main()
{
  // ---- 1) 上游畸形语料必须被拒（内嵌上游 malformed_example3.json 的前 2 个对象，上游共 7 个；截断即可稳定触发词法拒绝）----
  const char *malformed =
    "[\n\t{\n\t\tcolor: \"red\",\n\t\tvalue: \"#f00\"\n\t},\n\t{\n"
    "\t\tcolor: \"green\",\n\t\tvalue: \"#0f0\"\n\t}\n]\n";
  bool thrown = false;
  JAULA::Exception::ExCode code = JAULA::Exception::NO_ERROR;
  try
  {
    std::istringstream in(malformed);
    JAULA::Value_Complex *v = JAULA::Parser::parseStream(in);
    delete v;
  }
  catch (JAULA::Exception &e)
  {
    thrown = true;
    code = e.getCode();
  }
  check(thrown, "upstream malformed_example3.json is rejected");
  check(code == JAULA::Exception::SYNTAX_ERROR || code == JAULA::Exception::LEXAN_ERROR,
        "rejection carries a lexan/syntax error code");
  if (thrown)
    std::cout << "malformed rejected with code=" << static_cast<int>(code) << std::endl;

  // ---- 2) 未闭合数组同样是语法错误 ----
  bool truncated_thrown = false;
  try
  {
    std::istringstream in("[ 1, 2");
    JAULA::Value_Complex *v = JAULA::Parser::parseStream(in);
    delete v;
  }
  catch (JAULA::Exception &e)
  {
    truncated_thrown = true;
  }
  check(truncated_thrown, "truncated array is rejected");

  // ---- 3) 类型收窄必须抛 BAD_DATA_TYPE ----
  bool bad_type_thrown = false;
  JAULA::Exception::ExCode bad_code = JAULA::Exception::NO_ERROR;
  try
  {
    JAULA::Value_String dst;
    JAULA::Value_Number_Int src(5);
    dst.set(src);
  }
  catch (JAULA::Exception &e)
  {
    bad_type_thrown = true;
    bad_code = e.getCode();
  }
  check(bad_type_thrown, "assigning an integer into a string value is rejected");
  check(bad_code == JAULA::Exception::BAD_DATA_TYPE,
        "that rejection uses the BAD_DATA_TYPE code");

  // ---- 4) 重复键必须抛 NAME_DUPLICATED ----
  bool dup_thrown = false;
  JAULA::Exception::ExCode dup_code = JAULA::Exception::NO_ERROR;
  try
  {
    JAULA::Value_Object obj;
    obj.insertItem("k", JAULA::Value_Number_Int(1));
    obj.insertItem("k", JAULA::Value_Number_Int(2));
  }
  catch (JAULA::Exception &e)
  {
    dup_thrown = true;
    dup_code = e.getCode();
  }
  check(dup_thrown, "duplicate object key is rejected");
  check(dup_code == JAULA::Exception::NAME_DUPLICATED,
        "that rejection uses the NAME_DUPLICATED code");

  return finish("test_errors");
}
