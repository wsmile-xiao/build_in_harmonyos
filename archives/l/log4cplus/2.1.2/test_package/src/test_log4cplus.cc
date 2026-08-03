// test_log4cplus.cc — 消费者视角验证 log4cplus API 正常工作
#include <cstdio>
#include <log4cplus/logger.h>
#include <log4cplus/loggingmacros.h>
#include <log4cplus/consoleappender.h>
#include <log4cplus/loglevel.h>

int main() {
    int passed = 0, failed = 0;

    printf("log4cplus Test Suite\n");
    printf("===================\n\n");

    // Test 1: 初始化日志库
    printf("Test 1: Initialization\n");
    log4cplus::initialize();
    printf("  ✓ log4cplus::initialize() OK\n");
    passed++;

    // Test 2: Logger 创建与名称验证
    printf("Test 2: Logger creation\n");
    log4cplus::Logger logger = log4cplus::Logger::getInstance("test.logger");
    if (logger.getName() == "test.logger") {
        printf("  ✓ Logger name: %s\n", logger.getName().c_str());
        passed++;
    } else {
        printf("  ✗ Logger name mismatch: %s\n", logger.getName().c_str());
        failed++;
    }

    // Test 3: ConsoleAppender 创建与日志写入
    printf("Test 3: ConsoleAppender and log write\n");
    {
        log4cplus::SharedAppenderPtr appender(new log4cplus::ConsoleAppender());
        appender->setName("console");
        logger.addAppender(appender);
        LOG4CPLUS_INFO(logger, "log4cplus test message");
        printf("  ✓ Logger/Appender/LOG4CPLUS_INFO OK\n");
        passed++;
    }

    // Test 4: Root logger 级别检测
    printf("Test 4: Root logger level\n");
    log4cplus::Logger root = log4cplus::Logger::getRoot();
    if (root.getLogLevel() >= log4cplus::DEBUG_LOG_LEVEL &&
        root.getLogLevel() <= log4cplus::OFF_LOG_LEVEL) {
        printf("  ✓ Root logger level: %d\n", root.getLogLevel());
        passed++;
    } else {
        printf("  ✗ Root logger level out of range: %d\n", root.getLogLevel());
        failed++;
    }

    printf("\n========== Summary ==========\n");
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
