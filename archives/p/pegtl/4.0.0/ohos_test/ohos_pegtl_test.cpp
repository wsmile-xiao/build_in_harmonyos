// pegtl 4.0.0 OHOS 专项测试：验证在 OpenHarmony (OHOS) 工具链下
// 使用公开头文件 <tao/pegtl.hpp> 构建 PEG 解析器并实际运行。
// 业务场景：解析 OHOS 包管理风格的一行键值配置（name=value; 分号分隔），
// 验证公开 API tao::pegtl::parse / must / seq / plus / star / one / sor 等可用。
#include <tao/pegtl.hpp>
#include <cstdio>
#include <string>
#include <vector>

namespace pegtl = tao::pegtl;

// 语法：identifier = [a-zA-Z_][a-zA-Z0-9_]*; value = [^;\n]*; kv = identifier '=' value;
namespace grammar {
  struct ident_char : pegtl::ranges<'0', '9', 'A', 'Z', '_', '_', 'a', 'z'> {};
  struct ident_head : pegtl::ranges<'A', 'Z', '_', '_', 'a', 'z'> {};
  struct ident : pegtl::seq<ident_head, pegtl::star<ident_char>> {};
  struct value : pegtl::star<pegtl::not_at<pegtl::one<';', '\n'>>, pegtl::any> {};
  struct kv : pegtl::seq<ident, pegtl::one<'='>, value> {};
  struct entry : pegtl::seq<pegtl::star<pegtl::space>, kv, pegtl::one<';'>> {};
  struct grammar : pegtl::must<pegtl::star<entry>, pegtl::eof> {};
}

// 动作：收集 name -> value
template <typename Rule>
struct collect : pegtl::nothing<Rule> {};
template <>
struct collect<grammar::ident> {
  template <typename Input>
  static void apply(const Input& in, std::vector<std::pair<std::string, std::string>>& kv) {
    kv.emplace_back(in.string(), std::string());
  }
};
template <>
struct collect<grammar::value> {
  template <typename Input>
  static void apply(const Input& in, std::vector<std::pair<std::string, std::string>>& kv) {
    if (!kv.empty()) { kv.back().second = in.string(); }
  }
};

int main() {
  const std::string cfg = "bundleName=com.example.demo; version=1.0.0; apiLevel=12;";
  std::vector<std::pair<std::string, std::string>> kv;
  pegtl::view_input<> in(cfg);
  bool ok = pegtl::parse<grammar::grammar, collect>(in, kv);
  if (!ok) { std::fprintf(stderr, "PEGTL OHOS parse FAILED\n"); return 1; }
  std::printf("PEGTL OHOS parse OK, %zu entries\n", kv.size());
  for (const auto& p : kv) {
    std::printf("  %s = %s\n", p.first.c_str(), p.second.c_str());
  }
  if (kv.size() != 3) { std::fprintf(stderr, "entry count mismatch\n"); return 2; }
  if (kv[0].first != "bundleName" || kv[0].second != "com.example.demo") { return 3; }
  if (kv[1].first != "version" || kv[1].second != "1.0.0") { return 4; }
  if (kv[2].first != "apiLevel" || kv[2].second != "12") { return 5; }
  std::printf("OHOS_SPECIFIC_TEST PASS\n");
  return 0;
}
