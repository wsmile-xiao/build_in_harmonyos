// mailio API 功能测试程序。
// R34：必须实质调用被测包的 API。
#include <mailio/message.hpp>
#include <mailio/mime.hpp>
#include <mailio/mailboxes.hpp>
#include <iostream>
#include <string>

int main() {
    // 使用 mailio API 构造 MIME 消息
    mailio::message msg;
    msg.from(mailio::mail_address("Test Sender", "test@example.com"));
    msg.add_recipient(mailio::mail_address("Test Recipient", "recipient@example.com"));
    msg.subject("Hello from mailio");
    msg.content("This is a test message body.");

    // 将消息格式化为字符串（覆盖 MIME 格式化代码路径）
    std::string formatted;
    msg.format(formatted);

    // 验证格式化输出非空且包含预期头部
    if (formatted.empty()) {
        std::cerr << "ERROR: formatted message is empty" << std::endl;
        return 1;
    }

    // 检查关键头部是否存在
    if (formatted.find("From:") == std::string::npos) {
        std::cerr << "ERROR: From header missing" << std::endl;
        return 1;
    }
    if (formatted.find("Subject:") == std::string::npos) {
        std::cerr << "ERROR: Subject header missing" << std::endl;
        return 1;
    }

    // 验证内容是否存在
    if (formatted.find("This is a test message body.") == std::string::npos) {
        std::cerr << "ERROR: message content missing" << std::endl;
        return 1;
    }

    std::cout << "mailio test passed!" << std::endl;
    return 0;
}
