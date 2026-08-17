// Trantor test_package — verifies core trantor subsystems link and
// instantiate on OHOS: EventLoop, InetAddress (Socket address),
// Resolver (DNS), and SSLContext (TLS via OpenSSL).
//
// NOTE: checks use explicit `return 1` on failure instead of assert(),
// so they remain effective under Release builds (NDEBUG) and ctest
// reports a non-zero exit code on any regression.
#include <trantor/net/EventLoop.h>
#include <trantor/net/InetAddress.h>
#include <trantor/net/Resolver.h>
#include <trantor/net/TcpConnection.h>  // SSLContext, SSLContextPtr, newSSLContext
#include <trantor/net/TLSPolicy.h>      // TLSPolicy
#include <trantor/utils/Logger.h>

#include <iostream>

// CHECK macro: prints a failure message and returns 1 from main.
// Works under both Debug and Release builds (no NDEBUG dependency).
#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (!(cond)) {                                              \
            std::cerr << "[FAIL] " << (msg) << std::endl;          \
            return 1;                                               \
        }                                                           \
    } while (0)

int main()
{
    trantor::Logger::setLogLevel(trantor::Logger::kWarn);

    // ── EventLoop: core event loop must construct ──
    trantor::EventLoop loop;
    std::cout << "[ok] EventLoop constructed" << std::endl;

    // ── InetAddress (Socket address): IPv4 + IPv6 endpoint construction ──
    trantor::InetAddress addr4("127.0.0.1", 8080);
    CHECK(addr4.family() == AF_INET, "InetAddress IPv4 family mismatch");
    CHECK(addr4.toIp() == "127.0.0.1", "InetAddress IPv4 toIp mismatch");
    CHECK(addr4.toIpPort() == "127.0.0.1:8080", "InetAddress IPv4 toIpPort mismatch");
    std::cout << "[ok] InetAddress IPv4: " << addr4.toIpPort() << std::endl;

    trantor::InetAddress addr6("::1", 8080, true);
    CHECK(addr6.family() == AF_INET6, "InetAddress IPv6 family mismatch");
    CHECK(addr6.toIp() == "::1", "InetAddress IPv6 toIp mismatch");
    std::cout << "[ok] InetAddress IPv6: " << addr6.toIpPort() << std::endl;

    // ── Resolver (DNS): asynchronous DNS resolver must instantiate ──
    auto resolver = trantor::Resolver::newResolver(&loop);
    CHECK(resolver != nullptr, "Resolver instantiation returned nullptr");
    std::cout << "[ok] Resolver (DNS) instantiated" << std::endl;

    // ── SSLContext (TLS): verify OpenSSL-backed TLS context links ──
    // Build a client-side TLSPolicy and construct an SSLContext to
    // confirm openssl linkage on OHOS.
    auto tlsPolicy = trantor::TLSPolicy::defaultClientPolicy();
    auto sslCtx = trantor::newSSLContext(*tlsPolicy, /*isServer=*/false);
    CHECK(sslCtx != nullptr, "newSSLContext returned nullptr");
    std::cout << "[ok] SSLContext (TLS) instantiated" << std::endl;

    std::cout << "All trantor subsystem tests passed!" << std::endl;
    return 0;
}
