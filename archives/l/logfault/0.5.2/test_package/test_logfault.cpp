/**
 * 消费者测试 — logfault 0.5.2（header-only 交付形态）
 *
 * 以消费者视角 include <logfault/logfault.h>（来自 conan 包的 include/ 交付件），
 * 真实调用 LFLOG_* 六级宏、LFLOG_IFALL_* 条件宏、StreamHandler/ProxyHandler、
 * LogManager 级别控制，覆盖：
 *   1. 六个日志级别的输出与级别名（ERROR/WARNING/NOTICE/INFO/DEBUGGING/TRACE）；
 *   2. 流式参数拼接（数字入流）；
 *   3. LFLOG_IFALL_* 在 LOGFAULT_ENABLE_ALL 下可用；
 *   4. 级别过滤语义：不相关的日志**参数不求值**（副作用计数器恒 0）；
 *   5. ProxyHandler 收到的 Message 字段（msg_ / level_）与 Handler 级别门限；
 *   6. LogManager SetLevel/GetLoglevel/IsRelevant/ClearHandlers 控制面。
 * 逐条打印读数（PASS/FAIL + got），任何一条失败即退出码非 0。
 *
 * 断言口径：18 条运行期 check（consumer 计数，不进上游分母）+ 1 条编译期
 * static_assert（枚举序，单列不混口径）。
 */
#define LOGFAULT_ENABLE_ALL
#include <logfault/logfault.h>

#include <cstdio>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>

// 编译期断言：交付头自报 LogLevel 枚举序（DISABLED=0 … TRACE=6）
static_assert(static_cast<int>(logfault::LogLevel::DISABLED) == 0 &&
                  static_cast<int>(logfault::LogLevel::ERROR) == 1 &&
                  static_cast<int>(logfault::LogLevel::WARN) == 2 &&
                  static_cast<int>(logfault::LogLevel::NOTICE) == 3 &&
                  static_cast<int>(logfault::LogLevel::INFO) == 4 &&
                  static_cast<int>(logfault::LogLevel::DEBUGGING) == 5 &&
                  static_cast<int>(logfault::LogLevel::TRACE) == 6,
              "logfault LogLevel enumeration layout changed");

static int g_total = 0;
static int g_failed = 0;

static void Check(const char *name, bool ok, const std::string &detail)
{
    ++g_total;
    if (ok) {
        std::printf("[consumer] PASS %-56s %s\n", name, detail.c_str());
    } else {
        ++g_failed;
        std::printf("[consumer] FAIL %-56s %s\n", name, detail.c_str());
    }
}

// 与上游 tests/default_to_clog.cpp 同法：把 std::clog 的流缓冲截进内存，
// 读取即清空（Take），保证每条 check 只看自己的输出。
static std::stringstream g_logbuf;
static std::streambuf *g_orig_clog = nullptr;

static std::string Take()
{
    const std::string s = g_logbuf.str();
    g_logbuf.str("");
    g_logbuf.clear();
    return s;
}

static bool Has(const std::string &haystack, const char *needle)
{
    return haystack.find(needle) != std::string::npos;
}

int main()
{
    using namespace logfault;

    g_orig_clog = std::clog.rdbuf(g_logbuf.rdbuf());
    auto &mgr = LogManager::Instance();

    // ── StreamHandler：六级日志与级别名 ────────────────────────────────
    mgr.SetHandler(std::make_unique<StreamHandler>(std::clog, LogLevel::TRACE));

    std::string out = Take();
    LFLOG_ERROR << "consumer-error";
    out = Take();
    Check("LFLOG_ERROR -> level name + message",
          Has(out, "ERROR") && Has(out, "consumer-error"), "got=" + out);

    LFLOG_WARN << "consumer-warn";
    out = Take();
    Check("LFLOG_WARN -> WARNING + message",
          Has(out, "WARNING") && Has(out, "consumer-warn"), "got=" + out);

    LFLOG_NOTICE << "consumer-notice";
    out = Take();
    Check("LFLOG_NOTICE -> NOTICE + message",
          Has(out, "NOTICE") && Has(out, "consumer-notice"), "got=" + out);

    LFLOG_INFO << "consumer-info";
    out = Take();
    Check("LFLOG_INFO -> INFO + message",
          Has(out, "INFO") && Has(out, "consumer-info"), "got=" + out);

    LFLOG_DEBUG << "consumer-debug";
    out = Take();
    Check("LFLOG_DEBUG -> DEBUGGING + message",
          Has(out, "DEBUGGING") && Has(out, "consumer-debug"), "got=" + out);

    LFLOG_TRACE << "consumer-trace";
    out = Take();
    Check("LFLOG_TRACE -> TRACE + message",
          Has(out, "TRACE") && Has(out, "consumer-trace"), "got=" + out);

    // 流式参数（ostream 可流式的一切皆可记录）
    LFLOG_INFO << "streamed-n=" << 42 << "-end";
    out = Take();
    Check("streaming non-string args into log line",
          Has(out, "streamed-n=42-end"), "got=" + out);

    // LFLOG_IFALL_* 在 LOGFAULT_ENABLE_ALL 下生效
    LFLOG_IFALL_INFO("ifall-enabled");
    out = Take();
    Check("LFLOG_IFALL_INFO evaluated with LOGFAULT_ENABLE_ALL",
          Has(out, "ifall-enabled"), "got=" + out);

    // ── 级别过滤：不相关的日志参数不求值（README 契约）─────────────────
    mgr.SetHandler(std::make_unique<StreamHandler>(std::clog, LogLevel::WARN));
    (void)Take();
    int side_effects = 0;
    const auto bump = [&side_effects] {
        ++side_effects;
        return 7;
    };
    LFLOG_INFO << "hidden-" << bump();
    out = Take();
    Check("filtered INFO produces no output",
          out.empty(), "got=\"" + out + "\"");
    Check("filtered INFO does not evaluate arguments (side effects==0)",
          side_effects == 0, "got=" + std::to_string(side_effects));

    LFLOG_ERROR << "still-visible";
    out = Take();
    Check("ERROR passes WARN-level filter",
          Has(out, "still-visible"), "got=" + out);

    // ── ProxyHandler：Message 字段 ─────────────────────────────────────
    std::string proxied;
    LogLevel proxied_level = LogLevel::DISABLED;
    int proxy_calls = 0;
    mgr.SetHandler(std::make_unique<ProxyHandler>(
        [&proxied, &proxied_level, &proxy_calls](const Message &m) {
            proxied = m.msg_;
            proxied_level = m.level_;
            ++proxy_calls;
        },
        LogLevel::DEBUGGING));
    LFLOG_DEBUG << "proxy-payload";
    Check("ProxyHandler receives message payload",
          proxy_calls == 1 && proxied == "proxy-payload",
          "calls=" + std::to_string(proxy_calls) + " msg=" + proxied);
    Check("ProxyHandler sees LogLevel::DEBUGGING",
          proxied_level == LogLevel::DEBUGGING,
          "level=" + Handler::LevelName(proxied_level));

    // ── Handler 级别门限：ERROR 档 handler 不接收 INFO ─────────────────
    proxy_calls = 0;
    mgr.ClearHandlers();
    mgr.AddHandler(std::make_unique<ProxyHandler>(
        [&proxy_calls](const Message &) { ++proxy_calls; }, LogLevel::ERROR));
    LFLOG_INFO << "not-for-error-handler";
    Check("ERROR-level handler does not receive INFO",
          proxy_calls == 0, "calls=" + std::to_string(proxy_calls));
    LFLOG_ERROR << "for-error-handler";
    Check("ERROR-level handler receives ERROR",
          proxy_calls == 1, "calls=" + std::to_string(proxy_calls));

    // ── 控制面：SetLevel / GetLoglevel / IsRelevant / ClearHandlers ────
    mgr.SetLevel(LogLevel::NOTICE);
    Check("SetLevel/GetLoglevel round-trip (NOTICE)",
          mgr.GetLoglevel() == LogLevel::NOTICE,
          "level=" + Handler::LevelName(mgr.GetLoglevel()));
    Check("IsRelevant honors current level",
          !mgr.IsRelevant(LogLevel::INFO) && mgr.IsRelevant(LogLevel::ERROR),
          "info=false error=true");

    mgr.ClearHandlers();
    Check("ClearHandlers disables logging (IsRelevant==false)",
          !mgr.IsRelevant(LogLevel::ERROR), "IsRelevant=false");

    std::clog.rdbuf(g_orig_clog);
    std::printf("[consumer] summary: %d/%d checks passed (runtime), "
                "compile-time static_assert=1\n",
                g_total - g_failed, g_total);
    return g_failed == 0 ? 0 : 1;
}
