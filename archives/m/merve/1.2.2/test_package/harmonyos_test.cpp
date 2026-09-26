// 鸿蒙特有测试：在 OHOS(musl + libc++) 上验证 merve 的平台相关行为——
// 平台标识宏、C ABI 从 C++ 调用、字节导向的 UTF-8 与换行统计、多线程并发解析、
// 大输入与反复分配释放。断言语义取自上游 tests/ 的既有用例。
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

#include "merve.h"
#include "merve_c.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                        \
  do {                                                                     \
    ++g_checks;                                                            \
    if (!(cond)) {                                                         \
      ++g_failed;                                                          \
      std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond);           \
    }                                                                      \
  } while (0)

static bool c_string_eq(merve_string value, const char* expected) {
  const size_t length = std::strlen(expected);
  return value.length == length && std::memcmp(value.data, expected, length) == 0;
}

// OHOS 上 C++ 运行时与 libc++ 的 thread_local 错误态由 musl 提供。
static void check_platform_identity() {
#ifdef __OHOS__
  const bool ohos = true;
#else
  const bool ohos = false;
#endif
  CHECK(ohos);
  CHECK(std::strcmp(merve_get_version(), MERVE_VERSION) == 0);

  const merve_version_components parts = merve_get_version_components();
  CHECK(parts.major == 1);
  CHECK(parts.minor == 2);
  CHECK(parts.revision == 2);
}

// 非 ASCII 键名按 UTF-8 字节长度返回，musl 不做 locale 转换。
static void check_utf8_export_names() {
  const char* source = "exports['α'] = 54; exports['⨉'] = 45; exports['not identifier'] = 1;";
  const merve_analysis result = merve_parse_commonjs(source, std::strlen(source));
  CHECK(result != nullptr);
  CHECK(merve_is_valid(result));
  CHECK(merve_get_exports_count(result) == 3);
  if (merve_get_exports_count(result) == 3) {
    CHECK(c_string_eq(merve_get_export_name(result, 0), "α"));
    CHECK(merve_get_export_name(result, 0).length == 2);
    CHECK(c_string_eq(merve_get_export_name(result, 1), "⨉"));
    CHECK(merve_get_export_name(result, 1).length == 3);
    CHECK(c_string_eq(merve_get_export_name(result, 2), "not identifier"));
  }
  merve_free(result);
}

// LF / CRLF 两种换行都要给出同样的 1-based 行号与字节列号。
static void check_line_endings() {
  const char* lf = "// line 1\nexports.x = 1;\n";
  merve_error_loc loc{123, 456};
  merve_analysis result = merve_parse_commonjs(lf, std::strlen(lf), &loc);
  CHECK(merve_is_valid(result));
  CHECK(merve_get_exports_count(result) == 1);
  CHECK(merve_get_export_line(result, 0) == 2);
  merve_free(result);

  const char* crlf = "\r\n  import 'x';";
  merve_error_loc bad{123, 456};
  result = merve_parse_commonjs(crlf, std::strlen(crlf), &bad);
  CHECK(!merve_is_valid(result));
  CHECK(merve_get_last_error() == MERVE_ERROR_UNEXPECTED_ESM_IMPORT);
  CHECK(bad.line == 2);
  CHECK(bad.column == 3);
  merve_free(result);
}

// 4 个 OS 线程并发解析同一个大输入，结果必须一致（musl 线程 + 全局错误态隔离在解析结果里）。
static void check_concurrent_parsing() {
  std::string source;
  source.reserve(64 * 1024);
  for (int i = 0; i < 2000; ++i) {
    source += "exports.name" + std::to_string(i) + " = " + std::to_string(i) + ";\n";
  }
  CHECK(source.size() > 32768);

  std::vector<std::thread> workers;
  std::vector<size_t> counts(4, 0);
  for (size_t thread = 0; thread < 4; ++thread) {
    workers.emplace_back([&source, &counts, thread]() {
      const merve_analysis result = merve_parse_commonjs(source.data(), source.size());
      counts[thread] = merve_get_exports_count(result);
      merve_free(result);
    });
  }
  for (std::thread& worker : workers) {
    worker.join();
  }
  for (size_t thread = 0; thread < 4; ++thread) {
    CHECK(counts[thread] == 2000);
  }
}

// 反复解析/释放，验证分配器在 musl 上稳定回收。
static void check_repeated_allocation() {
  const char* source = "module.exports = { a, b, c };";
  bool stable = true;
  for (int i = 0; i < 4000; ++i) {
    const merve_analysis result = merve_parse_commonjs(source, std::strlen(source));
    if (!merve_is_valid(result) || merve_get_exports_count(result) != 3) {
      stable = false;
    }
    merve_free(result);
  }
  CHECK(stable);

  // 输入不保证 null 终止：只允许读 [data, data + length)，其后的字节不得参与解析。
  std::string padded = std::string("exports.foo = 1;") + "TRAILING-JUNK-NOT-SOURCE";
  const size_t meaningful = std::strlen("exports.foo = 1;");
  const merve_analysis sliced = merve_parse_commonjs(padded.data(), meaningful);
  CHECK(merve_is_valid(sliced));
  CHECK(merve_get_exports_count(sliced) == 1);
  if (merve_get_exports_count(sliced) == 1) {
    CHECK(c_string_eq(merve_get_export_name(sliced, 0), "foo"));
  }
  merve_free(sliced);
}

int main() {
  check_platform_identity();
  check_utf8_export_names();
  check_line_endings();
  check_concurrent_parsing();
  check_repeated_allocation();

  std::printf("MERVE_CONSUMER_RESULT name=harmonyos_test checks=%d failed=%d\n",
              g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
