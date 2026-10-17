// HarmonyOS 专项测试: lunarlog 在 OHOS 平台的真实运行验证。
// 覆盖: (1) 公开 API 结构化日志写入 OHOS 可写路径 (TMPDIR, /tmp 只读场景);
//       (2) 多线程并发日志 (OHOS pthread); (3) culture 格式化在无 locale 数据
//       的 OHOS 环境优雅回退 C 行为(不崩溃, 不产生无效输出)。
#include <lunar_log.hpp>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>
#include <vector>

int main() {
    // OHOS 上 /tmp 只读(erofs), 必须使用 TMPDIR 语义的目录。
    const char* tdir = getenv("TMPDIR");
    std::string logPath = std::string(tdir ? tdir : ".") + "/ohos_specific_test.log";
    std::remove(logPath.c_str());

    minta::LunarLog logger(minta::LogLevel::TRACE);
    logger.addSink<minta::FileSink>(logPath);

    // 1) 公开 API 消息模板
    logger.info("OHOS test {lib} v{ver}", "lib", "lunarlog", "ver", 1.29);
    logger.flush();

    // 2) 多线程并发日志
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&logger, i]() {
            for (int j = 0; j < 50; ++j) logger.debug("thread {t} msg {m}", "t", i, "m", j);
        });
    }
    for (auto& t : threads) t.join();
    logger.flush();

    // 3) culture 格式化: 无 locale 数据时回退 C (不崩溃)
    std::string n = minta::detail::applyFormat("1234567.89", "n", "en_US");
    if (n.empty()) {
        std::printf("FAIL: culture format empty\n");
        return 1;
    }

    // 验证日志确实写入并包含模板展开内容
    FILE* f = fopen(logPath.c_str(), "r");
    if (!f) {
        std::printf("FAIL: log file not created at %s\n", logPath.c_str());
        return 1;
    }
    std::string content;
    char buf[1024];
    size_t infoLines = 0, debugLines = 0;
    while (fgets(buf, sizeof(buf), f)) {
        content += buf;
        if (std::string(buf).find("OHOS test") != std::string::npos) infoLines++;
        if (std::string(buf).find("msg") != std::string::npos) debugLines++;
    }
    fclose(f);
    if (infoLines != 1 || debugLines != 200) {
        std::printf("FAIL: infoLines=%zu debugLines=%zu\n", infoLines, debugLines);
        return 1;
    }
    if (content.find("lunarlog") == std::string::npos) {
        std::printf("FAIL: template expansion missing\n");
        return 1;
    }
    std::printf("PASS: OHOS specific test ok (log=%s bytes=%zu, culture fallback='%s')\n",
                logPath.c_str(), content.size(), n.c_str());
    return 0;
}
