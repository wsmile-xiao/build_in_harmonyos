// cajun-jsonapi 2.1.1 — HarmonyOS/aarch64 专项测试 (task cajun-jsonapi-2.1.1-r01-pc1-47)
//
// 1) UTF-8 多字节字符串往返：鸿蒙系统默认 UTF-8 语言环境，验证含中文的
//    多字节字符串经 Reader/Writer 往返后内容逐字节一致。
// 2) 双精度 Number 往返精度：arm64 IEEE-754 双精度，验证非整数（含
//    负指数）经序列化/反序列化后值级一致。
// 3) 异常路径：对畸形文档，Reader 必须抛出 json::ParseException /
//    json::ScanException（上游测试未覆盖异常类型断言，本测试补足）。
// 4) 嵌套 Object+Array 大文档往返：验证深层结构读路径。
#include <cassert>
#include <cstdio>
#include <sstream>
#include <string>

#include "cajun/json/reader.h"
#include "cajun/json/writer.h"
#include "cajun/json/elements.h"

static void test_utf8_roundtrip()
{
   json::Object doc;
   doc["title"] = json::String("鸿蒙PC适配");
   doc["author"] = json::String("cajun-jsonapi-测试");
   doc["zh"] = json::String("简体中文-é-€");

   std::ostringstream out;
   json::Writer::Write(doc, out, false);

   json::UnknownElement root;
   std::istringstream in(out.str());
   json::Reader::Read(root, in);

   std::string title = json::String(root["title"]);
   std::string author = json::String(root["author"]);
   std::string zh = json::String(root["zh"]);
   assert(title == "鸿蒙PC适配");
   assert(author == "cajun-jsonapi-测试");
   assert(zh == "简体中文-é-€");
   std::printf("  [ok] UTF-8 multibyte round-trip: %s\n", title.c_str());
}

static void test_double_precision_roundtrip()
{
   json::Object doc;
   doc["pi"] = json::Number(3.141592653589793);
   doc["small"] = json::Number(2.5e-8);
   doc["neg"] = json::Number(-12345.678);

   std::ostringstream out;
   json::Writer::Write(doc, out, false);

   json::UnknownElement root;
   std::istringstream in(out.str());
   json::Reader::Read(root, in);

   assert(json::Number(root["pi"]).Value() == 3.141592653589793);
   assert(json::Number(root["small"]).Value() == 2.5e-8);
   assert(json::Number(root["neg"]).Value() == -12345.678);
   std::printf("  [ok] double precision round-trip\n");
}

static void test_exception_paths()
{
   // 缺少逗号 -> ParseException
   bool parseCaught = false;
   try {
      json::Object o;
      std::istringstream bad("{\"a\":1 \"b\":2}");
      json::Reader::Read(o, bad);
   } catch (const json::Reader::ParseException&) {
      parseCaught = true;
   }
   assert(parseCaught);

   // 完全非 JSON 内容 -> ScanException
   bool scanCaught = false;
   try {
      json::Object o;
      std::istringstream bad("not json at all");
      json::Reader::Read(o, bad);
   } catch (const json::Reader::ScanException&) {
      scanCaught = true;
   }
   assert(scanCaught);
   std::printf("  [ok] exception paths (ParseException/ScanException)\n");
}

static void test_nested_roundtrip()
{
   json::Object root;
   json::Array records;
   for (int i = 0; i < 3; ++i) {
      json::Object rec;
      rec["id"] = json::Number(static_cast<double>(i));
      json::Array tags;
      tags.Insert(json::String("t0"));
      tags.Insert(json::String("t1"));
      rec["tags"] = tags;
      records.Insert(rec);
   }
   root["records"] = records;

   std::ostringstream out;
   json::Writer::Write(root, out, true);

   json::UnknownElement parsed;
   std::istringstream in(out.str());
   json::Reader::Read(parsed, in);

   json::Array arr = json::Array(parsed["records"]);
   assert(arr.Size() == 3);
   for (int i = 0; i < 3; ++i) {
      json::Object rec = json::Object(arr[static_cast<size_t>(i)]);
      assert(static_cast<double>(json::Number(rec["id"])) == static_cast<double>(i));
      json::Array tags = json::Array(rec["tags"]);
      assert(tags.Size() == 2);
   }
   std::printf("  [ok] nested Object+Array round-trip\n");
}

int main()
{
   std::printf("cajun-jsonapi OHOS specialty tests (aarch64/UTF-8/exceptions)\n");
   test_utf8_roundtrip();
   test_double_precision_roundtrip();
   test_exception_paths();
   test_nested_roundtrip();
   std::printf("cajun-jsonapi test_ohos: ALL PASSED\n");
   return 0;
}
