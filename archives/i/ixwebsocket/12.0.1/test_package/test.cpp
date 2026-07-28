// test.cpp — IXWebSocket consumer test (L1 test)
// Tests the IXUrlParser API from the IXWebSocket library.
// This test calls the real IXWebSocket API to verify the library is usable.

#include <ixwebsocket/IXUrlParser.h>
#include <ixwebsocket/IXWebSocketVersion.h>
#include <iostream>
#include <string>

int main() {
    // Verify IXWebSocket version string is available
    std::string version(IX_WEBSOCKET_VERSION);
    std::cout << "IXWebSocket version: " << version << std::endl;
    if (version.empty()) {
        std::cerr << "FAIL: IX_WEBSOCKET_VERSION is empty" << std::endl;
        return 1;
    }

    // Test URL parsing — a core IXWebSocket utility function
    std::string protocol, host, path, query;
    int port = 0;

    bool ok = ix::UrlParser::parse(
        "https://example.com:8443/ws",
        protocol, host, path, query, port
    );

    if (ok && protocol == "https" && host == "example.com" && port == 8443) {
        std::cout << "IXWebSocket URL parser test passed!" << std::endl;
        std::cout << "  protocol=" << protocol << std::endl;
        std::cout << "  host=" << host << std::endl;
        std::cout << "  port=" << port << std::endl;
        std::cout << "  path=" << path << std::endl;
        return 0;
    }

    std::cerr << "IXWebSocket URL parser test failed!" << std::endl;
    std::cerr << "  ok=" << ok << " protocol=" << protocol
              << " host=" << host << " port=" << port << std::endl;
    return 1;
}
