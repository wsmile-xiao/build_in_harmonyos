// Consumer test: build an RFC 5322 message with wmime and verify generation.
#include <iostream>
#include <locale>
#include <clocale>
#include <sstream>

#include "vmime/vmime.hpp"
#include "vmime/platforms/posix/posixHandler.hpp"

static int check(bool cond, const char* name) {
    if (cond) {
        std::cout << "CHECK-OK: " << name << std::endl;
        return 0;
    }
    std::cout << "CHECK-FAIL: " << name << std::endl;
    return 1;
}

int main() {
    try {
        std::locale::global(std::locale(""));
    } catch (...) {
        std::setlocale(LC_ALL, "");
    }
    vmime::platform::setHandler<vmime::platforms::posix::posixHandler>();

    int failures = 0;
    try {
        vmime::messageBuilder mb;
        mb.setExpeditor(vmime::mailbox("me@somewhere.com"));

        vmime::addressList to;
        to.appendAddress(vmime::make_shared<vmime::mailbox>("you@elsewhere.com"));
        mb.setRecipients(to);
        mb.setSubject(vmime::text("libwmime consumer test"));
        mb.getTextPart()->setText(
            vmime::make_shared<vmime::stringContentHandler>("hello hmbs consumer")
        );

        vmime::shared_ptr<vmime::message> msg = mb.construct();
        failures += check(msg != nullptr, "message-constructed");

        std::ostringstream oss;
        vmime::utility::outputStreamAdapter out(oss);
        msg->generate(out);
        std::string raw = oss.str();
        failures += check(!raw.empty(), "message-generated-nonempty");
        failures += check(raw.find("libwmime consumer test") != std::string::npos,
                          "subject-roundtrip");
        failures += check(raw.find("me@somewhere.com") != std::string::npos,
                          "from-roundtrip");
        failures += check(raw.find("you@elsewhere.com") != std::string::npos,
                          "to-roundtrip");
        failures += check(raw.find("hello hmbs consumer") != std::string::npos,
                          "body-roundtrip");
    } catch (vmime::exception& e) {
        std::cout << "CHECK-FAIL: vmime-exception: " << e.what() << std::endl;
        return 1;
    } catch (std::exception& e) {
        std::cout << "CHECK-FAIL: std-exception: " << e.what() << std::endl;
        return 1;
    }
    if (failures == 0) {
        std::cout << "TEST-PASS: test_message_build" << std::endl;
    }
    return failures == 0 ? 0 : 1;
}
