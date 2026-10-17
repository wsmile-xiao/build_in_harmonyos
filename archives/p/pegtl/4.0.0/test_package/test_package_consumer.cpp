// test_package 消费者用例：仅通过 pegtl 已安装的公开头文件与公开 API 使用该库，
// 验证第三方（OHOS）消费者能否编译、链接、调用并正常运行。
// 业务场景：用 PEGTL 解析一行"键=值"配置并校验结果（公开 API: tao::pegtl::parse / must / seq / one / ranges / eof / string_input）。
#include <tao/pegtl.hpp>
#include <cstdio>
#include <string>

namespace pegtl = tao::pegtl;

namespace grammar {
  struct key : pegtl::plus<pegtl::ranges<'a', 'z', 'A', 'Z', '_', '_'>> {};
  struct val : pegtl::star<pegtl::not_at<pegtl::one<'\n'>>, pegtl::any> {};
  struct line : pegtl::seq<key, pegtl::one<'='>, val> {};
  struct grammar : pegtl::must<line, pegtl::eof> {};
}

int main() {
  const std::string input = "apiLevel=12";
  pegtl::view_input<> in(input);
  if (!pegtl::parse<grammar::grammar>(in)) {
    std::fprintf(stderr, "consumer parse FAILED\n");
    return 1;
  }
  std::printf("consumer parse OK\n");
  return 0;
}