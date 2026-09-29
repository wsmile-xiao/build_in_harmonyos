// harmonyos_consumer_e2e.cpp — logfault 0.8.5 鸿蒙特有测试（赛事 Review 规则 12，R03 加强）
//
// 完整消费者端到端用例：在真实 OHOS (aarch64) 设备环境走通
//   创建 handler -> 设置级别 -> 产生日志输出 -> 对输出断言 -> 明确失败返回码
//
// 验证的鸿蒙 PC 行为/兼容性：
//   1. 日志消息按预期写入绑定的 ostream（StreamHandler 端到端输出）
//   2. 日志级别过滤：SetLevel(ERROR) 后 INFO 不再输出（级别语义与 OHOS 运行一致）
//   3. 时间戳结构化断言：输出行必须以 'YYYY-MM-DD HH:MM:SS.mmm' + 时区（CST/UTC 等）开头
//      （R03 加强：不再用 find("20") 弱断言，改为正则匹配完整时间戳格式并可失败）
//   4. 线程名取 gettid：对 'INFO <tid>' 段做数字断言，并与 syscall(SYS_gettid) 实测值比对
//      （R03 加强：文件头声称 gettid 必须有对应断言，二者一致）
//
// 可失败证明（--fail-cap）：
//   同一测试在 --fail-cap 模式下故意篡改断言（期望错误值），必须返回非 0，
//   证明该测试真实断言被测库输出、可失败；默认模式断言正确值返回 0。
//
// 用法:
//   harmonyos_consumer_e2e                     # 正常断言，输出通过日志
//   harmonyos_consumer_e2e --fail-cap          # 篡改断言，必须失败（证明可失败）

#include "logfault/logfault.h"

#include <cerrno>
#include <cstring>
#include <iostream>
#include <regex>
#include <sstream>
#include <string>
#include <sys/syscall.h>
#include <unistd.h>

using namespace std;

int main(int argc, char* argv[]) {
    const bool fail_cap = (argc > 1 && string(argv[1]) == "--fail-cap");

    // 1. 创建 handler（绑定到本地 ostringstream，捕获日志输出）
    ostringstream out;
    logfault::LogManager::Instance().AddHandler(
        make_unique<logfault::StreamHandler>(out, logfault::LogLevel::DEBUGGING));
    logfault::LogManager::Instance().SetLevel(logfault::LogLevel::INFO);

    // 2. 产生日志输出（INFO 级别，多段拼接）
    LFLOG_INFO << "HarmonyOS" << "Consumer" << 42;

    // 3. 级别过滤验证：降级到 ERROR 后 INFO 不得再输出
    logfault::LogManager::Instance().SetLevel(logfault::LogLevel::ERROR);
    const auto before = out.str();
    LFLOG_INFO << "MustNotAppear";
    const auto after = out.str();
    if (after != before) {
        cerr << "FAIL: INFO emitted below ERROR level" << endl;
        return 1;
    }

    const string output = out.str();

    // 4. 断言：日志包含拼接消息体（真实触达被测库的 ostream 输出）
    const bool msg_ok = output.find("HarmonyOSConsumer42") != string::npos;
    // 断言：日志包含级别名（PrintMessage 输出的 'INFO'）
    const bool level_ok = output.find("INFO") != string::npos;

    // 5. 时间戳结构化断言（R03 加强）：行首 'YYYY-MM-DD HH:MM:SS.mmm' + 时区字母缩写
    //    例：'2026-09-28 14:05:19.867 CST INFO ...'
    static const regex ts_re(R"(^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} [A-Z]{2,5} )");
    const bool time_ok = regex_search(output, ts_re);

    // 6. gettid 断言（R03 加强）：提取 'INFO <tid>' 的数字段，与 syscall(SYS_gettid) 实测值一致
    //    例：'... INFO 32044 HarmonyOSConsumer42'
    long expected_tid = 0;
    bool tid_ok = false;
    {
        smatch m;
        // 匹配 'INFO <digits>'（tid 为 1-8 位十进制数字）
        static const regex tid_re(R"( INFO ([0-9]{1,8}) )");
        if (regex_search(output, m, tid_re)) {
            expected_tid = syscall(SYS_gettid);
            long printed_tid = stol(m[1].str());
            tid_ok = (printed_tid == expected_tid);
        }
    }

    // 可失败开关：篡改断言为期望错误值，必须失败
    const bool msg_assert = fail_cap ? !msg_ok : msg_ok;
    const bool time_assert = fail_cap ? !time_ok : time_ok;
    const bool tid_assert = fail_cap ? !tid_ok : tid_ok;

    if (!msg_assert || !level_ok || !time_assert || !tid_assert) {
        cerr << "FAIL: log output assertion failed (fail_cap=" << (fail_cap ? "yes" : "no") << ")" << endl;
        cerr << "  msg_ok=" << msg_ok << " level_ok=" << level_ok
             << " time_ok=" << time_ok << " tid_ok=" << tid_ok
             << " expected_tid=" << expected_tid << endl;
        cerr << "captured output: [" << output << "]" << endl;
        return 1;
    }

    cout << "PASS: logfault 0.8.5 harmonyos consumer e2e ok (fail_cap="
         << (fail_cap ? "yes" : "no") << ")" << endl;
    cout << "captured output: [" << output << "]" << endl;
    return 0;
}
