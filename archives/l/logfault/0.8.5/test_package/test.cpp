// test_package 消费者测试：真实调用 logfault 的公开 API（R34）
#include <logfault/logfault.h>

#include <iostream>
#include <sstream>
#include <string>

int main() {
    std::ostringstream buf;
    logfault::LogManager::Instance().AddHandler(
        std::make_unique<logfault::StreamHandler>(buf, logfault::LogLevel::DEBUGGING));
    logfault::LogManager::Instance().SetLevel(logfault::LogLevel::INFO);

    LFLOG_INFO << "Testing" << 1 << 2 << 3;

    std::string out = buf.str();
    if (out.find("Testing123") == std::string::npos) {
        std::cerr << "FAIL: expected 'Testing123' in log output, got: " << out << std::endl;
        return 1;
    }
    std::cout << "logfault 0.8.5 consumer test OK" << std::endl;
    return 0;
}