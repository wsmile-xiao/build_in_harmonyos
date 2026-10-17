// Consumer test for glaze 8.3.0 on OHOS.
// Exercises the public API surface most downstream users touch:
// aggregate reflection, write/read JSON, generic JSON DOM, BEVE binary
// round-trip + BEVE->JSON bridge, CSV, partial JSON-pointer writes, and
// error handling via glz::expected.
#include <cmath>
#include <cstdio>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include <glaze/glaze.hpp>
#include <glaze/util/expected.hpp>

namespace
{
   int failures = 0;

   void check(bool ok, const char* what)
   {
      if (not ok) {
         ++failures;
         std::printf("FAIL: %s\n", what);
      }
      else {
         std::printf("ok: %s\n", what);
      }
   }
} // namespace

// 反射元数据要求类型具有链接性，不能放在匿名命名空间
namespace test_types
{
   struct coordinates
   {
      double x{};
      double y{};
   };

   // glaze CSV 是列式表格语义：每个反射成员是一列（容器）
   struct csv_columns
   {
      std::vector<int> ids{};
      std::vector<double> vals{};
   };

   struct person
   {
      std::string name{};
      int age{};
      std::optional<std::string> nickname{};
      std::vector<double> scores{};
      coordinates home{};
   };
} // namespace test_types

using test_types::coordinates;
using test_types::csv_columns;
using test_types::person;

int main()
{
   // 1. Aggregate reflection: write + read back a struct.
   person p{};
   p.name = "ohos";
   p.age = 8;
   p.nickname = "glz";
   p.scores = {1.5, 2.5, 3.5};
   p.home = {116.4, 39.9};

   std::string buffer = glz::write_json(p).value_or("write failed");
   check(buffer.find("\"name\":\"ohos\"") != std::string::npos, "write_json serializes reflected members");

   person parsed{};
   auto ec = glz::read_json(parsed, buffer);
   check(!ec, "read_json parses without error");
   check(parsed.name == "ohos" && parsed.age == 8 && parsed.nickname.value_or("") == "glz" &&
            std::abs(parsed.home.y - 39.9) < 1e-9 && parsed.scores.size() == 3,
         "read_json round-trips all fields");

   // 2. prettify output still reflects the same data.
   std::string pretty = glz::write<glz::opts{.prettify = true}>(p).value_or("pretty failed");
   check(pretty.find('\n') != std::string::npos, "prettify output contains newlines");

   // 3. Generic JSON DOM.
   glz::generic dom{};
   auto dom_ec = glz::read_json(dom, R"({"a": 1, "b": [true, "x"], "c": {"d": 2.5}})");
   check(!dom_ec, "generic DOM parses nested JSON");
   check(dom["a"].get<double>() == 1.0, "DOM number access");
   check(dom["b"][1].get<std::string>() == "x", "DOM array string access");
   check(dom["c"]["d"].get<double>() == 2.5, "DOM nested double access");

   // 4. BEVE binary round-trip through JSON bridge.
   std::string beve = glz::write_beve(p).value_or("beve failed");
   check(!beve.empty(), "write_beve produces binary payload");
   person beve_parsed{};
   auto beve_ec = glz::read_beve(beve_parsed, beve);
   check(!beve_ec, "read_beve parses binary payload");
   check(beve_parsed.home.x == 116.4 && beve_parsed.scores.size() == 3, "BEVE round-trips fields");
   std::string bridged{};
   auto bridge_ec = glz::beve_to_json(beve, bridged);
   check(!bridge_ec, "beve_to_json bridges binary to JSON");
   check(bridged.find("ohos") != std::string::npos, "bridged JSON contains data");

   // 5. CSV round-trip on a columnar struct (colwise layout).
   csv_columns cs{{1, 2, 3}, {1.5, 2.5, 3.5}};
   std::string csv = glz::write_csv<glz::colwise>(cs).value_or("csv failed");
   check(csv.find("1.5") != std::string::npos && csv.find("3.5") != std::string::npos, "write_csv emits columns");
   csv_columns cs_in{};
   auto csv_ec = glz::read_csv<glz::colwise>(cs_in, csv);
   check(!csv_ec && cs_in.vals.size() == 3 && cs_in.vals[1] == 2.5, "read_csv round-trips columns");

   // 6. Partial serialization through JSON pointers.
   static constexpr auto selected = glz::json_ptrs("/name", "/age");
   std::string partial{};
   auto p_ec = glz::write_json<selected>(p, partial);
   check(!p_ec, "partial write via json_ptrs");
   check(partial.find("\"name\":\"ohos\"") != std::string::npos &&
            partial.find("\"scores\"") == std::string::npos,
         "partial write contains only selected keys");

   // 7. Error handling: malformed JSON yields an error via glz::expected.
   person bad{};
   auto bad_ec = glz::read_json(bad, std::string_view{R"({"name": })"});
   check(bool(bad_ec), "malformed JSON reports error");

   // 8. Map serialization.
   std::map<std::string, int> m{{"k1", 1}, {"k2", 2}};
   std::string m_json = glz::write_json(m).value_or("map failed");
   check(m_json == R"({"k1":1,"k2":2})", "map serializes in order");
   std::map<std::string, int> m_in{};
   check(!glz::read_json(m_in, m_json) && m_in["k2"] == 2, "map round-trips");

   if (failures != 0) {
      std::printf("%d check(s) FAILED\n", failures);
      return 1;
   }
   std::printf("all consumer checks passed\n");
   return 0;
}
