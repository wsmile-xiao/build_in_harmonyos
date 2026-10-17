#include <stdint.h>
#include <stddef.h>
#include <console_bridge/console.h>

#include <cstdio>
#include <string>
#include <vector>

// console_bridge 1.0.2 —— 真实行为验证（非 dlopen 空壳）。
// 装一个自定义 OutputHandler 截住日志，再断言：
//   ① 日志真的流到 handler（不是被吞掉）
//   ② printf 风格变参格式化在 OHOS/musl 上正确
//   ③ setLogLevel 阈值过滤真的生效
//   ④ file/line 如实传递
//   ⑤ noOutputHandler / restorePreviousOutputHandler 成对生效
// 这些都要求 libconsole_bridge.so 的 C++ 符号能被**链接**解析——dlopen 探针做不到。

static int failures = 0;

#define CHECK(cond, msg)                                                       \
  do {                                                                         \
    if (!(cond)) {                                                             \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__);   \
      ++failures;                                                              \
    } else {                                                                   \
      std::printf("[ok] %s\n", msg);                                           \
    }                                                                          \
  } while (0)

namespace {

struct Record {
  std::string text;
  console_bridge::LogLevel level;
  std::string file;
  int line;
};

class CapturingHandler : public console_bridge::OutputHandler {
 public:
  void log(const std::string &text, console_bridge::LogLevel level,
           const char *filename, int line) override {
    records.push_back(Record{text, level, filename ? filename : "", line});
  }
  std::vector<Record> records;
};

}  // namespace

int main() {
  CapturingHandler handler;
  console_bridge::useOutputHandler(&handler);

  // ① + ② + ④
  console_bridge::setLogLevel(console_bridge::CONSOLE_BRIDGE_LOG_DEBUG);
  console_bridge::log("probe.cpp", 42, console_bridge::CONSOLE_BRIDGE_LOG_INFO,
                      "value=%d name=%s ratio=%.2f", 7, "ohos", 1.5);

  CHECK(handler.records.size() == 1, "日志送达 handler（1 条）");
  if (handler.records.size() == 1) {
    const Record &r = handler.records[0];
    const bool fmt_ok = (r.text == "value=7 name=ohos ratio=1.50");
    CHECK(fmt_ok, "printf 风格变参格式化正确");
    if (!fmt_ok) std::fprintf(stderr, "       实得: \"%s\"\n", r.text.c_str());
    CHECK(r.level == console_bridge::CONSOLE_BRIDGE_LOG_INFO, "level 如实传递");
    CHECK(r.file == "probe.cpp" && r.line == 42, "file/line 如实传递");
  }

  // ③ 阈值过滤：抬到 ERROR 后 INFO/WARN 应被丢弃，ERROR 应放行
  handler.records.clear();
  console_bridge::setLogLevel(console_bridge::CONSOLE_BRIDGE_LOG_ERROR);
  CHECK(console_bridge::getLogLevel() == console_bridge::CONSOLE_BRIDGE_LOG_ERROR,
        "getLogLevel 读回设定值");

  console_bridge::log("f", 1, console_bridge::CONSOLE_BRIDGE_LOG_INFO, "info-should-drop");
  console_bridge::log("f", 2, console_bridge::CONSOLE_BRIDGE_LOG_WARN, "warn-should-drop");
  console_bridge::log("f", 3, console_bridge::CONSOLE_BRIDGE_LOG_ERROR, "error-should-pass");

  CHECK(handler.records.size() == 1, "阈值 ERROR 时只放行 1 条");
  if (handler.records.size() == 1)
    CHECK(handler.records[0].text == "error-should-pass", "放行的正是 ERROR 那条");

  // ⑤
  handler.records.clear();
  console_bridge::noOutputHandler();
  CHECK(console_bridge::getOutputHandler() == nullptr, "noOutputHandler 后 handler 为空");
  console_bridge::log("f", 4, console_bridge::CONSOLE_BRIDGE_LOG_ERROR, "swallowed");
  CHECK(handler.records.empty(), "关掉 handler 后日志不再送达");

  console_bridge::restorePreviousOutputHandler();
  CHECK(console_bridge::getOutputHandler() == &handler, "restore 恢复到自定义 handler");

  if (failures) {
    std::fprintf(stderr, "\nconsole_bridge: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nconsole_bridge 1.0.2: 全部断言通过\n");
  return 0;
}
