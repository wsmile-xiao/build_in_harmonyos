// 鸿蒙特有测试：在 OHOS(musl + libc++ + aarch64) 上验证 Jinx 的平台相关行为——
// 平台标识、64 位整数宽度、UTF-8 字节导向字符串、协程上下文切换、
// 每线程独立 runtime 的并发约束、反复分配释放的稳定性、大脚本编译。
// 断言语义取自上游 Tests/UnitTests 的既有用例（TestCasts/TestCoroutines/TestStrings）。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <thread>
#include <vector>

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

static ScriptPtr RunScript(const RuntimePtr &runtime, const char *text) {
  auto bytecode = runtime->Compile(text, "harmonyos");
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

static void check_platform_identity() {
#ifdef __OHOS__
  const bool ohos = true;
#else
  const bool ohos = false;
#endif
  CHECK(ohos);
  // 交付的头文件与库版本一致（消费者只看得到 <Jinx.h>）。
  CHECK(GetVersionString() == "1.3.10");
  // OHOS 的 LP64 数据模型：size_t 与 long 都是 64 位。
  CHECK(sizeof(void *) == 8);
  CHECK(sizeof(std::size_t) == 8);
  CHECK(sizeof(long) == 8);
}

static void check_int64_width() {
  // 2147483648 超出 int32，必须按 64 位整数保存而不是降级为浮点。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, "set big to 2147483648\nset neg to -9223372036854775807\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  const Variant big = script->GetVariable("big");
  CHECK(big.IsInteger());
  CHECK(big.GetInteger() == static_cast<int64_t>(2147483648));
  const Variant neg = script->GetVariable("neg");
  CHECK(neg.IsInteger());
  CHECK(neg.GetInteger() < 0);
}

static void check_utf8_string_bytes() {
  // musl 不做 locale 转换，字符串 Variant 按 UTF-8 字节存放：
  // 'α'=2 'β'=2 '⨉'=3 → 7 字节。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, "set s to \"αβ⨉\"\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  const Variant s = script->GetVariable("s");
  CHECK(s.IsString());
  const String text = s.GetString();
  CHECK(text.size() == 7);
  CHECK(std::memcmp(text.data(), "\xce\xb1\xce\xb2\xe2\xa8\x89", 7) == 0);
  // 逐字节比较与 const char* 重载在这里必须给出同一结论。
  CHECK(text == "αβ⨉");
}

static void check_coroutine_context_switch() {
  // 协程在 aarch64 上走真实的上下文切换，取上游 TestCoroutines 的同一段脚本。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime,
                          "import core\n"
                          "function test\n"
                          "    return 4242\n"
                          "end\n"
                          "set c to async call function test\n"
                          "wait until c is finished\n"
                          "set v to c's value\n");
  CHECK(script != nullptr);
  if (!script)
    return;
  CHECK(script->GetVariable("c").IsCoroutine());
  CHECK(script->GetVariable("v").IsInteger());
  CHECK(script->GetVariable("v").GetInteger() == 4242);
}

static void check_per_thread_runtime() {
  // Jinx 的 runtime 不能跨线程共享：每个线程各建一个 runtime，结果必须互不串扰。
  constexpr int kThreads = 4;
  std::vector<int> results(kThreads, -1);
  std::vector<std::thread> workers;
  for (int i = 0; i < kThreads; ++i) {
    workers.emplace_back([&results, i] {
      auto runtime = CreateRuntime();
      if (!runtime)
        return;
      const std::string source = "set n to " + std::to_string((i + 1) * 1000)
                                 + "\nset m to n + 7\n";
      auto script = RunScript(runtime, source.c_str());
      if (script)
        results[i] = static_cast<int>(script->GetVariable("m").GetInteger());
    });
  }
  for (auto &t : workers)
    t.join();
  for (int i = 0; i < kThreads; ++i)
    CHECK(results[i] == (i + 1) * 1000 + 7);
}

static void check_allocation_stability() {
  // 反复建/销毁 runtime 与脚本，验证 musl 分配器下没有句柄或状态泄漏导致的失败。
  int ok = 0;
  for (int i = 0; i < 2000; ++i) {
    auto runtime = CreateRuntime();
    auto script = RunScript(runtime, "set a to 6 * 7\n");
    if (script && script->GetVariable("a").GetInteger() == 42)
      ++ok;
  }
  CHECK(ok == 2000);

  // 最后一轮仍要给出正确结果。
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, "set a to 6 * 7\n");
  CHECK(script != nullptr);
  if (script)
    CHECK(script->GetVariable("a").GetInteger() == 42);
}

static std::string LargeScriptSource() {
  // 1000 条累加语句：编译期缓冲与运行期变量栈在设备内存策略下必须撑住。
  std::string source = "set total to 0\n";
  for (int i = 1; i <= 1000; ++i)
    source += "set total to total + " + std::to_string(i) + "\n";
  return source;
}

static void check_default_instruction_budget_is_enforced() {
  // Jinx::GlobalParams::maxInstructions 默认 2000。超预算必须让 Execute 返回 false，
  // 而不是在 aarch64/OHOS 上无界自旋或越界写。这一段必须在提高预算之前跑。
  const std::string source = LargeScriptSource();
  auto runtime = CreateRuntime();
  CHECK(runtime != nullptr);
  if (!runtime)
    return;
  auto script = RunScript(runtime, source.c_str());
  CHECK(script == nullptr);

  // 预算内的小脚本在同一 runtime 工厂仍然正常。
  auto small = RunScript(runtime, "set a to 1 + 2\n");
  CHECK(small != nullptr);
  if (small)
    CHECK(small->GetVariable("a").GetInteger() == 3);
}

static void raise_instruction_budget() {
  // 宿主集成方式取自上游 Tests/Features/Main.cpp:71 与 Tests/UnitTests/UnitTest.cpp:22。
  GlobalParams params;
  params.enableLogging = false;
  params.maxInstructions = std::numeric_limits<uint32_t>::max();
  params.logFn = [](LogLevel, const char *) {};
  Initialize(params);
}

static void check_large_script() {
  const std::string source = LargeScriptSource();
  auto runtime = CreateRuntime();
  auto script = RunScript(runtime, source.c_str());
  CHECK(script != nullptr);
  if (script) {
    const Variant total = script->GetVariable("total");
    CHECK(total.IsInteger());
    CHECK(total.GetInteger() == 500500);
  }
}

int main() {
  check_platform_identity();
  check_default_instruction_budget_is_enforced();
  raise_instruction_budget();
  check_int64_width();
  check_utf8_string_bytes();
  check_coroutine_context_switch();
  check_per_thread_runtime();
  check_allocation_stability();
  check_large_script();

  std::printf("JINX_HARMONYOS_RESULT assertions=%d failed=%d\n", g_checks, g_failed);
  return g_failed ? 1 : 0;
}
