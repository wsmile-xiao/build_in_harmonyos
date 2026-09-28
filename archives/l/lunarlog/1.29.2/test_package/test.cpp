// test_package consumer test — real usage of the lunarlog public API.
// Uses only installed public headers + public API (minta::LunarLog, FileSink).
#include <lunar_log.hpp>
#include <cstdio>
#include <string>

int main() {
    // Public API: structured logging with message templates.
    minta::LunarLog logger(minta::LogLevel::TRACE);
    logger.addSink<minta::FileSink>("consumer-test.log");

    logger.info("Hello {name} at {value}", "name", "lunarlog-consumer", "value", 42);
    logger.warn("Warning path");
    logger.error("Error path");
    logger.flush();

    // Verify the file was actually written with the formatted message.
    FILE *f = fopen("consumer-test.log", "r");
    if (!f) {
        std::printf("FAIL: consumer-test.log not created\n");
        return 1;
    }
    std::string content;
    char buf[512];
    while (fgets(buf, sizeof(buf), f)) content += buf;
    fclose(f);

    if (content.find("lunarlog-consumer") == std::string::npos) {
        std::printf("FAIL: formatted message not found in log\n");
        return 1;
    }
    std::printf("PASS: consumer wrote and read log via public API (%zu bytes)\n", content.size());
    return 0;
}
