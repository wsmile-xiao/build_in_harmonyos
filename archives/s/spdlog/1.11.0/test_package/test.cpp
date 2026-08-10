/* spdlog 1.11.0 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 日志真的写对了。这里把日志导进内存流，
 * 再断言**写出来的字符串本身**，覆盖几条核心契约：格式化转发给 fmt、
 * 自定义 pattern、级别过滤、flush。
 *
 * 这条链同时验证 SPDLOG_FMT_EXTERNAL 真的生效：spdlog 用的是外部 fmt 8.1.1
 * 而非自带副本。ad-map 系同时依赖 fmt 与 spdlog，两者必须是同一份 fmt ——
 * 同进程里两套 fmt 符号会打架。
 *
 * ⚠️ 消费方必须拿到 SPDLOG_FMT_EXTERNAL 宏。缺了它，spdlog/fmt/fmt.h 会走
 *    bundled 分支去 include spdlog/fmt/bundled/core.h，而那套头压根没装进包
 *    （实撞：'spdlog/fmt/bundled/core.h' file not found）。宏由配方的
 *    cpp_info.defines 传出，不是靠这里 #define —— 在这里定义只能糊住本文件，
 *    真正的消费方仍然会炸。
 */
#include "spdlog/spdlog.h"
#include "spdlog/sinks/ostream_sink.h"

#include <cstdio>
#include <memory>
#include <sstream>
#include <string>

static int fail(const char *what, const std::string &got, const char *want)
{
    std::printf("FAIL %s\n  实得: [%s]\n  期望包含: [%s]\n", what, got.c_str(), want);
    return 1;
}

int main(void)
{
    std::ostringstream oss;
    auto sink = std::make_shared<spdlog::sinks::ostream_sink_mt>(oss);
    auto log = std::make_shared<spdlog::logger>("t", sink);

    /* ① 纯消息模式：把 pattern 收成只剩正文，便于精确对账 */
    log->set_pattern("%v");
    log->set_level(spdlog::level::trace);

    log->info("hello");
    log->flush();
    if (oss.str().find("hello") == std::string::npos) {
        return fail("基本写入", oss.str(), "hello");
    }

    /* ② 格式化转发给 fmt —— 这是 spdlog 与 fmt 的接缝 */
    oss.str("");
    log->info("{} + {} = {}", 1, 2, 3);
    log->flush();
    if (oss.str().find("1 + 2 = 3") == std::string::npos) {
        return fail("fmt 转发", oss.str(), "1 + 2 = 3");
    }

    /* ③ fmt 的对齐/精度说明符也要能穿透过来 */
    oss.str("");
    log->info("[{:>6}] {:.3f}", "ab", 3.14159265);
    log->flush();
    if (oss.str().find("[    ab] 3.142") == std::string::npos) {
        return fail("fmt 说明符", oss.str(), "[    ab] 3.142");
    }

    /* ④ 级别过滤：设为 warn 后 info 不该落盘 */
    oss.str("");
    log->set_level(spdlog::level::warn);
    log->info("should-not-appear");
    log->warn("should-appear");
    log->flush();
    {
        const std::string s = oss.str();
        if (s.find("should-not-appear") != std::string::npos) {
            std::printf("FAIL 级别过滤失效：warn 级别下 info 仍被写出\n  实得: [%s]\n",
                        s.c_str());
            return 1;
        }
        if (s.find("should-appear") == std::string::npos) {
            return fail("级别过滤（warn 应写出）", s, "should-appear");
        }
    }

    /* ⑤ 自定义 pattern：级别名要按 pattern 出现 */
    oss.str("");
    log->set_level(spdlog::level::trace);
    log->set_pattern("[%l] %v");
    log->error("boom");
    log->flush();
    if (oss.str().find("[error] boom") == std::string::npos) {
        return fail("自定义 pattern", oss.str(), "[error] boom");
    }

    /* ⑥ 确认用的是外部 fmt：SPDLOG_FMT_EXTERNAL 必须已由包传进来。
     *    这一条防的是「宏没传、却因为 bundled 头恰好存在而静默编过」——
     *    那样两份 fmt 会同时在场。 */
#ifndef SPDLOG_FMT_EXTERNAL
    std::printf("FAIL 未收到 SPDLOG_FMT_EXTERNAL：包没把该宏传给消费方，"
                "spdlog 会改用自带的 fmt 副本\n");
    return 1;
#endif

    std::printf("spdlog OK: 写入/fmt 转发/说明符/级别过滤/pattern 共 5 组断言，"
                "且确认走外部 fmt（版本 %d.%d.%d）\n",
                SPDLOG_VER_MAJOR, SPDLOG_VER_MINOR, SPDLOG_VER_PATCH);
    return 0;
}
