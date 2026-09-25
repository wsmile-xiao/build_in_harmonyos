// cajun-jsonapi 2.1.1 — test_package 消费者验证
// 仅通过 Conan 包安装的公开头文件 (<cajun/json/...>) 使用公开 API：
// json::Reader / json::Writer / json::Object / json::Array /
// json::String / json::Number / json::Boolean，验证第三方使用者
// 能否编译、链接并正确解析/序列化 JSON（非空壳测试）。
#include <cassert>
#include <cstdio>
#include <sstream>
#include <string>

#include "cajun/json/reader.h"
#include "cajun/json/writer.h"
#include "cajun/json/elements.h"

int main()
{
   // 1) 用公开 API 构造 JSON 对象（业务场景：应用配置）
   json::Object doc;
   doc["app"] = json::String("ohos-demo");
   doc["version"] = json::String("2.1.1");
   json::Array features;
   features.Insert(json::String("json-parse"));
   features.Insert(json::String("json-write"));
   doc["features"] = features;
   doc["retries"] = json::Number(3);

   // 2) 序列化并回读（公开 API Writer::Write / Reader::Read）
   std::ostringstream out;
   json::Writer::Write(doc, out, false);
   std::string serialized = out.str();

   json::UnknownElement root;
   std::istringstream in(serialized);
   json::Reader::Read(root, in);

   // 3) 校验可观察结果：公开 operator[] 访问
   std::string app = json::String(root["app"]);
   assert(app == "ohos-demo");
   std::string ver = json::String(root["version"]);
   assert(ver == "2.1.1");
   assert(static_cast<double>(json::Number(root["retries"])) == 3.0);
   assert(static_cast<int>(json::Array(root["features"]).Size()) == 2);

   std::printf("test_package cajun-jsonapi: ALL PASSED (round-trip OK: %s)\n",
               serialized.c_str());
   return 0;
}
