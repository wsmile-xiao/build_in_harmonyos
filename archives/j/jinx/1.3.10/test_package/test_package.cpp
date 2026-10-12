// 消费者测试：只通过 Conan 交付的 <Jinx.h> + libJinx 使用公共 API，
// 断言语义取自上游 Tests/UnitTests 的既有用例（TestCasts/TestCollections/TestLoops/TestErrors）。
#include <cmath>
#include <cstdio>
#include <string>

#include "Jinx.h"

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

using namespace Jinx;

// 上游 Tests/UnitTests/UnitTest.cpp 的执行惯例：反复 Execute 直到 IsFinished()。
static ScriptPtr RunScript(const RuntimePtr &runtime, const char *text,
                           const char *name = "consumer") {
  auto bytecode = runtime->Compile(text, name);
  if (!bytecode)
    return nullptr;
  auto script = runtime->CreateScript(bytecode);
  if (!script)
    return nullptr;
  do {
    if (!script->Execute())
      return nullptr;
  } while (!script->IsFinished());
  return script;
}

static void check_library_identity() {
  // Jinx::String 带自定义分配器模板参数，比较一律走 basic_string 的 const char* 重载。
  const String version = GetVersionString();
  CHECK(!version.empty());
  CHECK(version == "1.3.10");
}

static void check_runtime_and_script() {
  auto runtime = CreateRuntime();
  CHECK(runtime != nullptr);

  auto script = RunScript(runtime, "set a to 123\n", "identity");
  CHECK(script != nullptr);
  if (script) {
    CHECK(script->GetName() == "identity");
    const Variant a = script->GetVariable("a");
    CHECK(a.IsInteger());
    CHECK(a.GetInteger() == 123);
  }
}

static void check_casts_match_upstream() {
  // 取自上游 TestCasts.cpp "Test variable casting" 的同一段脚本。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime,
                          "set a to 123.456 as integer\n"
                          "set b to true as string\n"
                          "set c to \"false\" as boolean\n"
                          "set e to \"-123.456\" as number\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  const Variant a = script->GetVariable("a");
  CHECK(a.IsInteger());
  CHECK(a.GetInteger() == 123);
  const Variant b = script->GetVariable("b");
  CHECK(b.IsString());
  CHECK(b.GetString() == "true");
  const Variant c = script->GetVariable("c");
  CHECK(c.IsBoolean());
  CHECK(c.GetBoolean() == false);
  const Variant e = script->GetVariable("e");
  CHECK(e.IsNumber());
  CHECK(std::fabs(e.GetNumber() - (-123.456)) < 1e-9);
}

static void check_collections_and_loops() {
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime,
                          "set a to 3, 2, 1\n"
                          "set total to 0\n"
                          "set i to 1\n"
                          "loop while i <= 10\n"
                          "    increment total by i\n"
                          "    increment i\n"
                          "end\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  const Variant a = script->GetVariable("a");
  CHECK(a.IsCollection());
  const CollectionPtr collection = a.GetCollection();
  CHECK(collection != nullptr);
  if (collection)
    CHECK(collection->size() == 3);
  const Variant total = script->GetVariable("total");
  CHECK(total.IsInteger());
  CHECK(total.GetInteger() == 55);
}

static void check_missing_and_reserved_variables() {
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, "set present to 1\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  CHECK(script->GetVariable("present").IsInteger());
  // 未声明的名字返回 Null，而不是让宿主崩溃。
  CHECK(script->GetVariable("never_declared").IsNull());
}

static void check_compile_error_is_rejected() {
  // 上游 TestErrors.cpp "Test missing comment block error" 用的是同一段文本。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, "---\n");
  CHECK(script == nullptr);
}

static void check_runtime_isolation_and_reuse() {
  auto first = CreateRuntime();
  auto second = CreateRuntime();
  CHECK(first != nullptr);
  CHECK(second != nullptr);
  if (!first || !second)
    return;

  auto scriptA = RunScript(first, "set shared_name to 11\n");
  auto scriptB = RunScript(second, "set shared_name to 22\n");
  CHECK(scriptA && scriptB);
  if (scriptA && scriptB) {
    CHECK(scriptA->GetVariable("shared_name").GetInteger() == 11);
    CHECK(scriptB->GetVariable("shared_name").GetInteger() == 22);
  }

  // 同一个 runtime 上再编译一个脚本，验证 runtime 可复用。
  auto scriptC = RunScript(first, "set extra to 7 * 6\n");
  CHECK(scriptC != nullptr);
  if (scriptC)
    CHECK(scriptC->GetVariable("extra").GetInteger() == 42);
}

int main() {
  check_library_identity();
  check_runtime_and_script();
  check_casts_match_upstream();
  check_collections_and_loops();
  check_missing_and_reserved_variables();
  check_compile_error_is_rejected();
  check_runtime_isolation_and_reuse();

  std::printf("JINX_CONSUMER_RESULT assertions=%d failed=%d\n", g_checks, g_failed);
  return g_failed ? 1 : 0;
}
