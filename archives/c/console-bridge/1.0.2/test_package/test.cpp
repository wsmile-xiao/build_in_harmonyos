/* console_bridge 1.0.2 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 日志真的转发对了。console_bridge 的全部职责
 * 就是「把日志调用转发给当前注册的 OutputHandler」，所以断言要落在那上面：
 * 装一个自己的 handler，发日志，检查它**收到的内容与级别**。
 *
 *   ① handler 真的被调用，收到的正文与级别都对
 *   ② 各级别（debug/inform/warn/error）分别走到对应的 LogLevel
 *   ③ setLogLevel 过滤生效 —— 低于阈值的不该转发
 *   ④ 恢复默认 handler 后不再往我们的 handler 送
 *
 * ③ 是最容易在移植中悄悄失效的一条：过滤逻辑坏掉不会报错，只会变成
 *   「日志全都打出来」或「一条都不打」，光看「跑通了」发现不了。
 */
#include <console_bridge/console.h>

#include <cstdio>
#include <string>
#include <vector>

namespace cb = console_bridge;

struct Rec {
    std::string text;
    cb::LogLevel level;
};

class Capture : public cb::OutputHandler {
public:
    std::vector<Rec> got;
    void log(const std::string &text, cb::LogLevel level,
             const char * /*filepath*/, int /*line*/) override
    {
        got.push_back(Rec{text, level});
    }
};

int main(void)
{
    Capture cap;
    cb::useOutputHandler(&cap);
    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_DEBUG);

    /* ① 基本转发 */
    CONSOLE_BRIDGE_logInform("hello %d", 42);
    if (cap.got.size() != 1) {
        std::printf("FAIL handler 收到 %zu 条，期望 1 条\n", cap.got.size());
        return 1;
    }
    if (cap.got[0].text != "hello 42") {
        std::printf("FAIL 正文 [%s] != [hello 42]\n", cap.got[0].text.c_str());
        return 1;
    }
    if (cap.got[0].level != cb::CONSOLE_BRIDGE_LOG_INFO) {
        std::printf("FAIL logInform 的级别 %d != CONSOLE_BRIDGE_LOG_INFO(%d)\n",
                    (int)cap.got[0].level, (int)cb::CONSOLE_BRIDGE_LOG_INFO);
        return 1;
    }

    /* ② 四个级别各自映射对 */
    cap.got.clear();
    CONSOLE_BRIDGE_logDebug("d");
    CONSOLE_BRIDGE_logInform("i");
    CONSOLE_BRIDGE_logWarn("w");
    CONSOLE_BRIDGE_logError("e");
    {
        const cb::LogLevel want[] = {
            cb::CONSOLE_BRIDGE_LOG_DEBUG, cb::CONSOLE_BRIDGE_LOG_INFO,
            cb::CONSOLE_BRIDGE_LOG_WARN,  cb::CONSOLE_BRIDGE_LOG_ERROR,
        };
        if (cap.got.size() != 4) {
            std::printf("FAIL 四级别共收到 %zu 条，期望 4 条\n", cap.got.size());
            return 1;
        }
        for (int i = 0; i < 4; ++i) {
            if (cap.got[i].level != want[i]) {
                std::printf("FAIL 第 %d 条级别 %d != %d\n",
                            i, (int)cap.got[i].level, (int)want[i]);
                return 1;
            }
        }
    }

    /* ③ 级别过滤：阈值设为 WARN 后，debug/inform 不该转发 */
    cap.got.clear();
    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_WARN);
    CONSOLE_BRIDGE_logDebug("should-not-appear");
    CONSOLE_BRIDGE_logInform("should-not-appear");
    CONSOLE_BRIDGE_logWarn("should-appear");
    CONSOLE_BRIDGE_logError("should-appear");
    if (cap.got.size() != 2) {
        std::printf("FAIL 阈值 WARN 下收到 %zu 条，期望 2 条"
                    "（过滤失效：要么全放过，要么全挡掉）\n", cap.got.size());
        for (size_t i = 0; i < cap.got.size(); ++i) {
            std::printf("  实收[%zu]: lvl=%d [%s]\n",
                        i, (int)cap.got[i].level, cap.got[i].text.c_str());
        }
        return 1;
    }
    for (size_t i = 0; i < cap.got.size(); ++i) {
        if (cap.got[i].text != "should-appear") {
            std::printf("FAIL 被过滤的消息漏了出来: [%s]\n", cap.got[i].text.c_str());
            return 1;
        }
    }
    if (cb::getLogLevel() != cb::CONSOLE_BRIDGE_LOG_WARN) {
        std::printf("FAIL getLogLevel() 取回 %d，与刚设的 WARN(%d) 不符\n",
                    (int)cb::getLogLevel(), (int)cb::CONSOLE_BRIDGE_LOG_WARN);
        return 1;
    }

    /* ④ 摘掉自定义 handler 后不该再收到 —— 验注册/注销这条链是对称的 */
    cap.got.clear();
    cb::restorePreviousOutputHandler();
    cb::setLogLevel(cb::CONSOLE_BRIDGE_LOG_DEBUG);
    CONSOLE_BRIDGE_logError("after-restore");
    if (!cap.got.empty()) {
        std::printf("FAIL 已恢复默认 handler，自定义 handler 仍收到 %zu 条\n",
                    cap.got.size());
        return 1;
    }

    std::printf("console-bridge OK: 转发/四级别映射/阈值过滤/handler 注销 共 4 组断言\n");
    return 0;
}
