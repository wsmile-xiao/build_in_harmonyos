// C1/C2a 用例：使用了 std::vector 但未直接 #include <vector>（IWYU 违规）。
// 期望 iwyu 报告 "should add these lines" 且含 `#include <vector>`；
// <iostream>/<string> 均被直接使用，不应被建议删除。
#include <iostream>
#include <string>

int main() {
  std::vector<std::string> v;
  v.push_back("hello");
  std::cout << v.size() << std::endl;
  return 0;
}
