// test_package 消费者测试 — 通过已安装公开头文件调用 cpp-smtpclient-library API
#include <smtpclient/messageaddress.h>
#include <smtpclient/plaintextmessage.h>
#include <smtpclient/attachment.h>
#include <cstdio>
#include <cstring>

using namespace jed_utils;

int main() {
    MessageAddress from("sender@example.com", "Sender");
    MessageAddress to("recipient@example.org");
    PlaintextMessage msg(from, to, "consumer subject", "consumer body");
    if (std::strcmp(msg.getSubject(), "consumer subject") != 0) {
        std::printf("FAIL: subject mismatch\n");
        return 1;
    }
    if (std::strcmp(msg.getMimeType(), "text/plain") != 0) {
        std::printf("FAIL: mime type mismatch\n");
        return 1;
    }
    Attachment att("missing.bin", "missing.bin");
    std::printf("test cpp-smtpclient-library 1.1.14: OK (subject=%s, mime=%s)\n",
                msg.getSubject(), msg.getMimeType());
    return 0;
}
