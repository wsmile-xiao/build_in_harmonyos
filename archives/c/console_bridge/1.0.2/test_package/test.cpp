#include <console_bridge/console.h>
#include <iostream>

int main() {
    std::cout << "Testing console_bridge library..." << std::endl;

    // 直接调用 console_bridge 命名空间内的导出函数 log()，
    // 传入文件名、行号、日志级别与消息内容。
    console_bridge::log(__FILE__, __LINE__,
                        console_bridge::CONSOLE_BRIDGE_LOG_INFO,
                        "Informational message");
    console_bridge::log(__FILE__, __LINE__,
                        console_bridge::CONSOLE_BRIDGE_LOG_WARN,
                        "Warning message");
    console_bridge::log(__FILE__, __LINE__,
                        console_bridge::CONSOLE_BRIDGE_LOG_ERROR,
                        "Error message");

    std::cout << "TEST PASSED" << std::endl;
    return 0;
}
