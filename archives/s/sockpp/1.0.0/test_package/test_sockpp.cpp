// test_sockpp.cpp — sockpp 1.0.0 消费者视角验证（Conan L1 / 层 2）
//
// 真实链接并调用 sockpp 公开 API，覆盖：
//   1) 版本指纹（包内 include/sockpp/version.h）
//   2) IPv4 地址对象与名字解析（getaddrinfo）
//   3) TCP 环回 accept / connect / write_n / read_n 收发
//   4) AF_UNIX socketpair 收发
// 断言总数 = PR 正文「鸿蒙特有测试」行取值来源（assertion_count）。
#include <sockpp/version.h>
#include <sockpp/inet_address.h>
#include <sockpp/tcp_acceptor.h>
#include <sockpp/tcp_connector.h>
#include <sockpp/unix_stream_socket.h>

#include <arpa/inet.h>
#include <tuple>
#include <iostream>
#include <string>

static int g_checks = 0;

#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FAIL assertion #" << g_checks << ": " #c << std::endl; \
            std::cerr << "check_summary: " << g_checks << " executed" << std::endl; \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main() {
    // ── 1. 版本指纹 ────────────────────────────────────────────────
    CHECK(sockpp::SOCKPP_VERSION_MAJOR == 1);
    CHECK(sockpp::SOCKPP_VERSION_MINOR == 0);
    CHECK(sockpp::SOCKPP_VERSION_PATCH == 0);
    CHECK(sockpp::SOCKPP_VERSION == "v1.0.0");

    // ── 2. IPv4 地址对象与解析 ────────────────────────────────────
    // inet_address::create() 内部做 htonl()，因此构造参数是主机序；
    // resolve_name() 返回网络序（与上游 test_inet_address.cpp 同口径）
    const uint32_t LOOPBACK_NET = htonl(INADDR_LOOPBACK);
    sockpp::inet_address loopback(INADDR_LOOPBACK, 0);
    CHECK(loopback.is_set());
    CHECK(loopback.family() == AF_INET);
    CHECK(loopback.address() == INADDR_LOOPBACK);
    CHECK(sockpp::inet_address::resolve_name("127.0.0.1") == LOOPBACK_NET);

    // ── 3. TCP 环回 accept / connect / 收发 ───────────────────────
    // 端口 0 = 由内核分配临时端口，避免与设备上其它任务争抢固定端口
    sockpp::inet_address bind_addr(INADDR_LOOPBACK, 0);
    sockpp::tcp_acceptor acc(bind_addr);
    CHECK(static_cast<bool>(acc));

    sockpp::inet_address bound(acc.address());
    CHECK(bound.port() != 0);

    sockpp::tcp_connector conn;
    CHECK(conn.connect(bound));

    sockpp::tcp_socket peer = acc.accept();
    CHECK(static_cast<bool>(peer));

    const std::string MSG { "sockpp-consumer-harmonyos" };
    const size_t N = MSG.size();
    CHECK(conn.write_n(MSG.data(), N) == static_cast<ssize_t>(N));

    char buf[64] = {0};
    CHECK(peer.read_n(buf, N) == static_cast<ssize_t>(N));
    CHECK(std::string(buf, N) == MSG);

    // ── 4. AF_UNIX socketpair 收发（无文件系统路径，不依赖可写 /tmp）──
    sockpp::unix_stream_socket u1, u2;
    std::tie(u1, u2) = sockpp::unix_stream_socket::pair();
    CHECK(static_cast<bool>(u1));
    CHECK(static_cast<bool>(u2));
    CHECK(u1.write_n(MSG.data(), N) == static_cast<ssize_t>(N));

    char ubuf[64] = {0};
    CHECK(u2.read_n(ubuf, N) == static_cast<ssize_t>(N));
    CHECK(std::string(ubuf, N) == MSG);

    std::cout << "sockpp test passed! check_summary: " << g_checks
              << " assertions OK, version " << sockpp::SOCKPP_VERSION
              << std::endl;
    return 0;
}
