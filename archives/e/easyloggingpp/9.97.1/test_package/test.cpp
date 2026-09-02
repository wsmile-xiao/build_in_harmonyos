// test_package consumer test for easyloggingpp 9.97.1
// Real, non-shell test: writes logs targeted at a writable path and
// asserts the log file content (levels, LOG_IF, LOG_EVERY_N).
// Consumer links the packaged static library (easyloggingpp::easyloggingpp).
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#include <easylogging++.h>

INITIALIZE_EASYLOGGINGPP

static const char* kLogFile = "elpp-consumer-test.log";

static int g_failures = 0;
#define TCHECK(cond, msg)                                          \
    do {                                                           \
        if (cond) {                                                \
            std::cout << "  [PASS] " << msg << std::endl;          \
        } else {                                                   \
            std::cout << "  [FAIL] " << msg << std::endl;          \
            ++g_failures;                                          \
        }                                                          \
    } while (0)

int main() {
    std::remove(kLogFile);

    el::Loggers::addFlag(el::LoggingFlag::ImmediateFlush);
    el::Configurations conf;
    conf.setGlobally(el::ConfigurationType::Format, "%datetime{%Y-%M-%d %H:%m:%s,%g} %level %msg");
    conf.setGlobally(el::ConfigurationType::Filename, kLogFile);
    conf.setGlobally(el::ConfigurationType::ToFile, "true");
    conf.setGlobally(el::ConfigurationType::ToStandardOutput, "false");
    conf.setGlobally(el::ConfigurationType::LogFlushThreshold, "1");
    el::Loggers::reconfigureLogger("default", conf);

    LOG(INFO) << "consumer-info";
    LOG(ERROR) << "consumer-error";
    LOG_IF(true, INFO) << "consumer-cond";
    for (int i = 1; i <= 4; ++i) {
        LOG_EVERY_N(2, INFO) << "consumer-every-n" << i;
    }

    std::ifstream f(kLogFile);
    std::stringstream ss;
    ss << f.rdbuf();
    std::string content = ss.str();

    TCHECK(content.find("consumer-info") != std::string::npos, "INFO 写入日志");
    TCHECK(content.find("consumer-error") != std::string::npos, "ERROR 写入日志");
    TCHECK(content.find("consumer-cond") != std::string::npos, "LOG_IF(true) 写入");
    TCHECK(content.find("consumer-every-n2") != std::string::npos, "EVERY_N(2) 第2次写");
    TCHECK(content.find("consumer-every-n4") != std::string::npos, "EVERY_N(2) 第4次写");

    std::remove(kLogFile);
    std::cout << (g_failures == 0 ? "easyloggingpp consumer test PASSED" : "easyloggingpp consumer test FAILED")
              << std::endl;
    return g_failures == 0 ? 0 : 1;
}