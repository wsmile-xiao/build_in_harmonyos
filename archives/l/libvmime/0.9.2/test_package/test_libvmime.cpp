// Consumer test for libvmime: build a MIME message with the public API
// and assert the RFC 822 output carries the headers we set.
#include <iostream>
#include <sstream>
#include <string>

#include <vmime/vmime.hpp>

static int fail(const char* what) {
    std::cerr << "FAIL: " << what << std::endl;
    return 1;
}

int main() {
    vmime::messageBuilder mb;
    mb.setExpeditor(vmime::mailbox("sender@ohos.dev"));

    vmime::addressList to;
    to.appendAddress(vmime::make_shared <vmime::mailbox>("rcpt@ohos.dev"));
    mb.setRecipients(to);

    mb.setSubject(vmime::text("ohos consumer test"));

    vmime::shared_ptr <vmime::message> msg = mb.construct();

    std::ostringstream oss;
    vmime::utility::outputStreamAdapter out(oss);
    msg->generate(out);

    const std::string rfc822 = oss.str();
    if (rfc822.find("From: sender@ohos.dev") == std::string::npos)
        return fail("From header missing");
    if (rfc822.find("ohos consumer test") == std::string::npos)
        return fail("Subject header missing");

    std::cout << "libvmime consumer test PASS" << std::endl;
    return 0;
}
