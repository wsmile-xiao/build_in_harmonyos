#include <console_bridge/console.h>

#include <cstdio>
#include <string>
#include <vector>

namespace cb = console_bridge;

struct Record {
    std::string text;
    cb::LogLevel level;
};

class Capture final : public cb::OutputHandler {
public:
    std::vector<Record> records;

    void log(const std::string &text, cb::LogLevel level,
             const char *, int) override
    {
        records.push_back({text, level});
    }
};

int main()
{
    int failures = 0;
#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            std::fprintf(stderr, "FAIL: %s\n", message); \
            ++failures; \
        } \
    } while (false)

    Capture capture;
    cb::useOutputHandler(&capture);
    CHECK(cb::getOutputHandler() == &capture, "自定义处理器已注册");

    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_DEBUG);
    CONSOLE_BRIDGE_logInform("hello %d", 42);
    CHECK(capture.records.size() == 1, "日志被转发一次");
    CHECK(!capture.records.empty() && capture.records[0].text == "hello 42",
          "格式化后的正文正确");
    CHECK(!capture.records.empty() &&
              capture.records[0].level == cb::CONSOLE_BRIDGE_LOG_INFO,
          "inform 映射为 INFO");

    capture.records.clear();
    CONSOLE_BRIDGE_logDebug("d");
    CONSOLE_BRIDGE_logInform("i");
    CONSOLE_BRIDGE_logWarn("w");
    CONSOLE_BRIDGE_logError("e");
    CHECK(capture.records.size() == 4, "四个日志级别均被转发");
    const cb::LogLevel expected[] = {
        cb::CONSOLE_BRIDGE_LOG_DEBUG,
        cb::CONSOLE_BRIDGE_LOG_INFO,
        cb::CONSOLE_BRIDGE_LOG_WARN,
        cb::CONSOLE_BRIDGE_LOG_ERROR,
    };
    bool levels_match = capture.records.size() == 4;
    for (std::size_t i = 0; levels_match && i < 4; ++i) {
        levels_match = capture.records[i].level == expected[i];
    }
    CHECK(levels_match, "四个日志级别的映射顺序正确");

    capture.records.clear();
    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_WARN);
    CONSOLE_BRIDGE_logDebug("drop-debug");
    CONSOLE_BRIDGE_logInform("drop-info");
    CONSOLE_BRIDGE_logWarn("keep-warn");
    CONSOLE_BRIDGE_logError("keep-error");
    CHECK(capture.records.size() == 2, "WARN 阈值过滤低级别日志");
    CHECK(cb::getLogLevel() == cb::CONSOLE_BRIDGE_LOG_WARN,
          "读取到刚设置的 WARN 阈值");

    capture.records.clear();
    cb::restorePreviousOutputHandler();
    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_DEBUG);
    CONSOLE_BRIDGE_logError("after-restore");
    CHECK(capture.records.empty(), "恢复处理器后不再转发到旧处理器");

    if (failures != 0) {
        std::fprintf(stderr, "console-bridge: %d 项断言失败\n", failures);
        return 1;
    }
    std::printf("console-bridge 1.0.1: 9 项消费者断言全部通过\n");
    return 0;
}
