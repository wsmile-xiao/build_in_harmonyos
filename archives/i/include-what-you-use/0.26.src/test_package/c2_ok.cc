// C2b 用例：#include 完全正确（IWYU 无违规）。
// 期望 iwyu + -Xiwyu --error 退出码 0，报告含 "has correct #includes/fwd-decls"。
#include <iostream>
#include <string>
#include <vector>

int main() {
  std::vector<std::string> v;
  v.push_back("hi");
  std::cout << v.size() << std::endl;
  return 0;
}
