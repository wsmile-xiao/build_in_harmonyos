// Consumer test for cpp-dump 0.7.0.
// Includes the installed header through the Conan package and exercises the
// public export_var() API with containers whose expected output is fixed by
// the upstream test fixtures (vector / ordered map / string).

#include <cpp-dump.hpp>

#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace cp = cpp_dump;

int main() {
  int failures = 0;

  // Compare against plain output: the default es_style=original wraps values in
  // ANSI color codes (observed on this platform), which would mask the format.
  cpp_dump::options::es_style = cpp_dump::types::es_style_t::no_es;

  // 1) std::vector formatting: "[ 1, 2, 3 ]"
  std::string vec_out = cp::export_var(std::vector<int>{1, 2, 3});
  if (vec_out.find("[ 1, 2, 3 ]") == std::string::npos) {
    std::cerr << "FAIL: unexpected vector output: " << vec_out << "\n";
    ++failures;
  }

  // 2) std::map formatting (ordered, deterministic): "{ 2: 6, 4: 6 }"
  std::string map_out = cp::export_var(std::map<int, int>{{2, 6}, {4, 6}});
  if (map_out.find("{ 2: 6, 4: 6 }") == std::string::npos) {
    std::cerr << "FAIL: unexpected map output: " << map_out << "\n";
    ++failures;
  }

  // 3) std::string quoting: "\"cpp-dump\""
  std::string str_out = cp::export_var(std::string("cpp-dump"));
  if (str_out.find("\"cpp-dump\"") == std::string::npos) {
    std::cerr << "FAIL: unexpected string output: " << str_out << "\n";
    ++failures;
  }

  if (failures != 0) {
    std::cerr << failures << " consumer check(s) failed\n";
    return 1;
  }
  std::cout << "cpp-dump consumer test passed\n";
  return 0;
}
