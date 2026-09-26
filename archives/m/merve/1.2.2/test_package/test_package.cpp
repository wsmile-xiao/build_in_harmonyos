// 消费者用例：通过 Conan 生成的 merve::merve 目标使用上游 C++ API。
// 断言语义全部取自上游 v1.2.2 的 tests/real_world_tests.cpp，避免自创预期。
#include <cstdio>
#include <cstring>
#include <string>

#include "merve.h"

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

static std::string view(const lexer::export_entry& entry) {
  return std::string(lexer::get_string_view(entry));
}

static void check_version_macros() {
  CHECK(std::strcmp(MERVE_VERSION, "1.2.2") == 0);
  CHECK(lexer::MERVE_VERSION_MAJOR == 1);
  CHECK(lexer::MERVE_VERSION_MINOR == 2);
  CHECK(lexer::MERVE_VERSION_REVISION == 2);
}

static void check_plain_and_bracket_exports() {
  auto result = lexer::parse_commonjs("exports.foo = 1; exports['bar'] = 2;");
  CHECK(result.has_value());
  CHECK(result->exports.size() == 2);
  if (result->exports.size() == 2) {
    CHECK(view(result->exports[0]) == "foo");
    CHECK(view(result->exports[1]) == "bar");
  }

  auto literal = lexer::parse_commonjs("module.exports = { a, b, c };");
  CHECK(literal.has_value());
  CHECK(literal->exports.size() == 3);
  if (literal->exports.size() == 3) {
    CHECK(view(literal->exports[0]) == "a");
    CHECK(view(literal->exports[1]) == "b");
    CHECK(view(literal->exports[2]) == "c");
  }

  auto reserved = lexer::parse_commonjs("exports.package = 'x'; exports.var = 'y';");
  CHECK(reserved.has_value());
  CHECK(reserved->exports.size() == 2);
  if (reserved->exports.size() == 2) {
    CHECK(view(reserved->exports[0]) == "package");
    CHECK(view(reserved->exports[1]) == "var");
  }
}

static void check_esbuild_and_typescript_patterns() {
  auto esbuild = lexer::parse_commonjs(
      "0 && (module.exports = {a, b, c}) && __exportStar(require('fs'));");
  CHECK(esbuild.has_value());
  CHECK(esbuild->exports.size() == 3);
  CHECK(esbuild->re_exports.size() == 1);
  if (esbuild->re_exports.size() == 1) {
    CHECK(view(esbuild->re_exports[0]) == "fs");
  }

  auto tsc = lexer::parse_commonjs(
      "\"use strict\";\
      function __export(m) {\
          for (var p in m) if (!exports.hasOwnProperty(p)) exports[p] = m[p];\
      }\
      Object.defineProperty(exports, \"__esModule\", { value: true });\
      __export(require(\"external1\"));\
      tslib.__export(require(\"external2\"));\
      __exportStar(require(\"external3\"));\
      tslib1.__exportStar(require(\"external4\"));\
      var color_factory_1 = require(\"./color-factory\");\
      Object.defineProperty(exports, \"colorFactory\", { enumerable: true, get: function () { return color_factory_1.colorFactory; }, });\
    ");
  CHECK(tsc.has_value());
  CHECK(tsc->exports.size() == 2);
  CHECK(tsc->re_exports.size() == 4);
  if (tsc->exports.size() == 2) {
    CHECK(view(tsc->exports[0]) == "__esModule");
    CHECK(view(tsc->exports[1]) == "colorFactory");
  }
  if (tsc->re_exports.size() == 4) {
    CHECK(view(tsc->re_exports[0]) == "external1");
    CHECK(view(tsc->re_exports[3]) == "external4");
  }

  auto getter = lexer::parse_commonjs(
      "Object.defineProperty(exports, 'a', {\
        enumerable: true,\
        get: function () {\
          return q.p;\
        }\
      });\
    ");
  CHECK(getter.has_value());
  CHECK(getter->exports.size() == 1);
  if (getter->exports.size() == 1) {
    CHECK(view(getter->exports[0]) == "a");
  }
}

static void check_line_numbers_and_empty_input() {
  auto result = lexer::parse_commonjs(
      "// line 1\n"
      "exports.a = 1;\n"
      "\n"
      "exports.b = 2;\n");
  CHECK(result.has_value());
  CHECK(result->exports.size() == 2);
  if (result->exports.size() == 2) {
    CHECK(result->exports[0].line == 2);
    CHECK(result->exports[1].line == 4);
  }

  auto empty = lexer::parse_commonjs("");
  CHECK(empty.has_value());
  CHECK(empty->exports.empty());
  CHECK(empty->re_exports.empty());
}

static void check_error_reporting() {
  auto failed = lexer::parse_commonjs("import 'x';");
  CHECK(!failed.has_value());
  const auto& error = lexer::get_last_error();
  CHECK(error.has_value());
  CHECK(error == lexer::lexer_error::UNEXPECTED_ESM_IMPORT);

  auto ok = lexer::parse_commonjs("exports.foo = 1;");
  CHECK(ok.has_value());
  CHECK(!lexer::get_last_error().has_value());
}

int main() {
  check_version_macros();
  check_plain_and_bracket_exports();
  check_esbuild_and_typescript_patterns();
  check_line_numbers_and_empty_input();
  check_error_reporting();

  std::printf("MERVE_CONSUMER_RESULT name=test_package checks=%d failed=%d\n",
              g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
