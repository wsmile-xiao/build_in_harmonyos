/* -*- coding: utf-8 -*-
 * 消费者测试 — pathie-cpp 0.1.1（test_package）
 *
 * 通过 Conan 导出的目标 Pathie::Pathie 链接被测包，覆盖：
 *   版本接口 / 路径归一 / basename·dirname·extension / 绝对相对判定 /
 *   join·prune / native 回转 / iconv 转码 / 流替换读写 / 目录建删。
 * 全部 12 条断言都在本进程内完成，文件操作只落在 test_package 构建目录。
 */

#include <pathie/pathie.hpp>
#include <pathie/path.hpp>
#include <pathie/pathie_ifstream.hpp>
#include <pathie/pathie_ofstream.hpp>

#include <cstring>
#include <iostream>
#include <string>

#include <cstdio>

static int g_checks = 0;
static int g_failed = 0;

static void check(const char* what, bool ok, const std::string& got = "")
{
  ++g_checks;
  if (ok) {
    std::cout << "[OK]   " << what << std::endl;
  } else {
    ++g_failed;
    std::cout << "[FAIL] " << what;
    if (!got.empty())
      std::cout << " (got: '" << got << "')";
    std::cout << std::endl;
  }
}

int main(int, char**)
{
  using namespace Pathie;

  // 1) 版本接口（上游以 PATHIE_VERSION_* 宏拼串）
  check("Pathie::version() == 0.1.1", version() == "0.1.1", version());

  // 2) 构造期 sanitize：折叠多余分隔符、去尾部 /
  check("Path(\"/usr//lib/\").str() == /usr/lib",
        Path("/usr//lib/").str() == "/usr/lib", Path("/usr//lib/").str());

  // 3) basename
  check("basename() == c.txt",
        Path("a/b/c.txt").basename().str() == "c.txt",
        Path("a/b/c.txt").basename().str());

  // 4) dirname
  check("dirname() == a/b",
        Path("a/b/c.txt").dirname().str() == "a/b",
        Path("a/b/c.txt").dirname().str());

  // 5) extension
  check("extension() == .txt",
        Path("a/b/c.txt").extension() == ".txt",
        Path("a/b/c.txt").extension());

  // 6) 绝对 / 相对判定
  check("is_absolute/is_relative",
        Path("/x").is_absolute() && Path("x").is_relative() && !Path("x").is_absolute());

  // 7) join
  check("join() == foo/bar/baz",
        Path("foo/bar").join("baz").str() == "foo/bar/baz",
        Path("foo/bar").join("baz").str());

  // 8) prune（就地消解 . 与 ..）
  check("prune() == bar", Path("foo/../bar").prune().str() == "bar",
        Path("foo/../bar").prune().str());

  // 9) native() 回转（与上游 test_native() 同口径：文件名编码往返，
  //    按 POSIX 只对 ASCII 稳定，故沿用上游的 ASCII 样本）
  check("native() round trip",
        Path("foo/bar").native() == "foo/bar", Path("foo/bar").native());

  // 10) iconv 转码（src/pathie.cpp convert_encodings，Linux/OHOS 由 libc 提供）
  check("convert_encodings(ISO-8859-1 -> UTF-8)",
        convert_encodings("ISO-8859-1", "UTF-8", std::string("\xe4")) == "\xc3\xa4",
        convert_encodings("ISO-8859-1", "UTF-8", std::string("\xe4")));

  // 11) 流替换组件读写回环（PATHIE_BUILD_STREAM_REPLACEMENTS=ON）
  {
    Path dir("pathie-tp-stream");
    dir.mkdir();
    Path file = dir.join("round trip.txt");

    Pathie::ofstream out(file, Pathie::ofstream::out);
    bool opened = out.is_open() && out.good();
    out << "pathie-tp-payload-42" << std::endl;
    out.close();
    check("Pathie::ofstream 写入", opened && file.exists());

    char buf[64];
    memset(buf, '\0', sizeof(buf));
    Pathie::ifstream in(file);
    bool in_open = in.is_open() && in.good();
    in.read(buf, sizeof(buf) - 1);
    in.close();
    check("Pathie::ifstream 读回 == pathie-tp-payload-42",
          in_open && std::string(buf) == "pathie-tp-payload-42\n", std::string(buf));

    dir.rmtree();
    check("rmtree() 清理", !dir.exists());
  }

  // 12) 目录建删
  {
    Path dir("pathie-tp-dir");
    dir.mkdir();
    bool made = dir.exists() && dir.is_directory();
    dir.rmdir();
    check("mkdir/exists/rmdir", made && !dir.exists());
  }

  std::cout << "SUMMARY checks=" << g_checks
            << " passed=" << (g_checks - g_failed)
            << " failed=" << g_failed << std::endl;
  return g_failed == 0 ? 0 : 1;
}
