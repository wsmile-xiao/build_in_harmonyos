// test_adql.cpp — 解析简单 ADQL SELECT 查询，验证 libadql 真实可用。
// 使用上游真实 API（与上游 test/parse_adql.cxx 一致）：
//   ADQL::Query query(sql, table_mapping);   // 构造 + 解析
//   std::string formatted = ADQL::to_string(query);
//   ADQL::Query reparsed(formatted);          // 再解析验证 round-trip
#include <ADQL/Query.hxx>
#include <ADQL/to_string.hxx>

#include <iostream>
#include <map>
#include <string>

int main() {
  // IVOA ADQL 2.0 查询（上游 parse_adql.cxx 真实用例格式——几何函数
  // 在 WHERE 子句，SELECT 列表为列名）：
  //   SELECT ra1,dec2,flux FROM mytable WHERE
  //   CONTAINS(POINT('j2000',ra,dec),CIRCLE('J2000',+10,-20,-1))= 1
  const std::string query_sql =
      "SELECT ra1,dec2,flux FROM mytable WHERE "
      "CONTAINS(POINT('j2000',ra,dec),CIRCLE('J2000',+10,-20,-1))= 1";
  std::map<std::string, std::string> table_mapping;
  try {
    ADQL::Query query(query_sql, table_mapping);
    std::string formatted = ADQL::to_string(query);
    if (formatted.empty()) {
      std::cerr << "FAIL: parsed query has empty SQL" << std::endl;
      return 1;
    }
    // round-trip：格式化后再解析，应与原格式化结果一致
    ADQL::Query reparsed(formatted);
    if (formatted != ADQL::to_string(reparsed)) {
      std::cerr << "FAIL: round-trip mismatch: " << formatted << std::endl;
      return 1;
    }
    std::cout << "PASS: parsed ADQL query -> " << formatted << std::endl;
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: parse threw: " << e.what() << std::endl;
    return 1;
  }
}
