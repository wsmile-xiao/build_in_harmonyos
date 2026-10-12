// 消费者用例：链接包内 libsbuild.a，调用其公共 API，并断言在 HarmonyOS PC
// （aarch64-linux-ohos，musl）上可以正常编译、链接与运行。
#include <cstdlib>
#include <iostream>
#include <string>
#include <unistd.h>

#include <sbuild/sbuild-util.h>

namespace {

int failures = 0;

void check(bool condition, std::string const& what) {
  std::cout << (condition ? "[PASS] " : "[FAIL] ") << what << '\n';
  if (!condition)
    ++failures;
}

void check_equal(std::string const& actual, std::string const& expected,
                 std::string const& what) {
  if (actual != expected)
    std::cout << "       actual='" << actual << "' expected='" << expected << "'\n";
  check(actual == expected, what);
}

} // namespace

int main() {
  check_equal(sbuild::basename("/usr/share/schroot/conf/schroot.conf"),
              "schroot.conf",
              "sbuild::basename() strips the directory part");
  check_equal(sbuild::basename("schroot.conf"), "schroot.conf",
              "sbuild::basename() keeps a bare filename");
  check_equal(sbuild::dirname("/usr/share/schroot/conf/schroot.conf"),
              "/usr/share/schroot/conf",
              "sbuild::dirname() strips the filename part");
  check_equal(sbuild::normalname("/usr//share/schroot/"), "/usr/share/schroot",
              "sbuild::normalname() removes duplicated and trailing separators");
  check(sbuild::is_absname("/usr"),
        "sbuild::is_absname() accepts an absolute path");
  check(!sbuild::is_absname("usr"),
        "sbuild::is_absname() rejects a relative path");
  check(!sbuild::is_valid_sessionname(".hidden"),
        "sbuild::is_valid_sessionname() rejects dotfiles");
  check(!sbuild::getcwd().empty(), "sbuild::getcwd() returns the working directory");
  check(sbuild::is_absname(sbuild::getcwd()),
        "sbuild::getcwd() returns an absolute path");
  check(!sbuild::unique_identifier().empty(),
        "sbuild::unique_identifier() returns a session identifier");

  // 平台断言：目标平台的 musl 动态加载器存在（aarch64-linux-ohos）。
  check(::access("/system/lib/ld-musl-aarch64.so.1", F_OK) == 0,
        "[OHOS] the musl dynamic loader of the target platform is present");

  std::cout << (failures == 0 ? "ALL CHECKS PASSED" : "CHECKS FAILED") << " ("
            << failures << " failure(s))\n";
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
