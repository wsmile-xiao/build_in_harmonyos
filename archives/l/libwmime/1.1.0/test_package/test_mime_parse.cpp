// Consumer test: parse a raw MIME message and verify structured fields.
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
        const char* rawMessage =
            "From: alice@example.com\r\n"
            "To: bob@example.com\r\n"
            "Subject: =?UTF-8?Q?mime-parse-check?=\r\n"
            "MIME-Version: 1.0\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Transfer-Encoding: quoted-printable\r\n"
            "\r\n"
            "Hello=20MIME=20parse=21\r\n";

        vmime::shared_ptr<vmime::message> msg =
            vmime::make_shared<vmime::message>();
        msg->parse(rawMessage);

        failures += check(msg->getHeader()->hasField("From"), "header-has-from");
        failures += check(msg->getHeader()->hasField("Subject"), "header-has-subject");

        vmime::shared_ptr<const vmime::headerFieldValue> subjValue =
            msg->getHeader()->findField("Subject")->getValue();
        const vmime::text* subjText =
            dynamic_cast<const vmime::text*>(subjValue.get());
        failures += check(subjText != nullptr, "subject-is-text");
        if (subjText != nullptr) {
            std::ostringstream oss;
            oss << subjText->getWholeBuffer();
            failures += check(oss.str().find("mime-parse-check") != std::string::npos,
                              "subject-decoded");
        }

        vmime::shared_ptr<const vmime::body> body = msg->getBody();
        failures += check(body != nullptr, "body-present");
        if (body != nullptr) {
            vmime::string decoded;
            vmime::utility::outputStreamStringAdapter out(decoded);
            body->getContents()->extract(out);
            failures += check(decoded.find("Hello MIME parse!") != std::string::npos,
                              "body-qp-decoded");
        }
    } catch (vmime::exception& e) {
        std::cout << "CHECK-FAIL: vmime-exception: " << e.what() << std::endl;
        return 1;
    } catch (std::exception& e) {
        std::cout << "CHECK-FAIL: std-exception: " << e.what() << std::endl;
        return 1;
    }
    if (failures == 0) {
        std::cout << "TEST-PASS: test_mime_parse" << std::endl;
    }
    return failures == 0 ? 0 : 1;
}
