#include <ucommon/ucommon.h>
#include <ucommon/secure.h>
#include <iostream>
#include <string>

using namespace ucommon;

int main() {
    // Test basic uCommon functionality
    String str("Hello from ucommon");
    std::cout << static_cast<const char *>(str) << std::endl;

    // Test threading support
    Thread::sleep(100);

    // Exercise the configured TLS backend when SSL support is enabled.
#if UCOMMON_WITH_SSL
    if (!secure::init()) {
        std::cerr << "secure backend initialization failed" << std::endl;
        return 1;
    }
#endif

    secure::string digest = Digest::sha256("ucommon");
    const char *digest_text = digest;
    if (!digest_text || std::string(digest_text) !=
        "488e0f7a8c61f4adb431e2e622065497ca101e25b1208d4ea90d0407e7d04501") {
        std::cerr << "SHA-256 digest check failed" << std::endl;
        return 1;
    }

    std::cout << "ucommon test passed" << std::endl;
    return 0;
}
