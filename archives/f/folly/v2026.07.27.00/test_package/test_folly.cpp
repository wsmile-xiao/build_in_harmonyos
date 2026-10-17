// test_folly.cpp — folly v2026.07.27.00 消费者冒烟测试
//
// 自选核心功能断言（与平台无关、确定性）：fbstring / Range / to / Format。
// 目的：以真实下游身份同时验证 编译期(头文件 C++20) + 链接期(Folly::folly
// 及其依赖链) + 运行期(返回码判定)，而非只编不链不跑。
#include <folly/FBString.h>
#include <folly/Range.h>
#include <folly/Format.h>
#include <folly/Conv.h>

#include <cstdio>
#include <string>

namespace {

void check(bool cond, const char* msg) {
  if (!cond) {
    std::fprintf(stderr, "FAIL: %s\n", msg);
    std::exit(1);
  }
}

} // namespace

int main() {
  // 1) fbstring：构造/拼接/比较（链接期真实拉入 libfolly_fbstring.a）
  folly::fbstring s = "hello";
  s += ", folly";
  check(s == "hello, folly", "fbstring concat");
  check(s.size() == 12, "fbstring size");

  // 2) Range：subpiece / 相等
  folly::StringPiece sp(s);
  check(sp.subpiece(0, 5) == "hello", "StringPiece subpiece");
  check(sp.startsWith("hello"), "StringPiece startsWith");

  // 3) to / Conv：数字↔字符串（链接 folly_conv）
  auto i = folly::to<int>("2026");
  check(i == 2026, "to<int>");
  auto str = folly::to<std::string>(20260727);
  check(str == "20260727", "to<string>");

  // 4) Format：格式化输出（链接 folly_format）
  auto fmtd = folly::format("{}-{:02d}", "v2026.07", 27).str();
  check(fmtd == "v2026.07-27", "folly::format");

  std::printf("folly consumer smoke OK\n");
  return 0;
}
