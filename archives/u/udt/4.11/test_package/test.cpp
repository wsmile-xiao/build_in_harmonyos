// UDT 4.11 consumer test — genuinely exercises the UDT library API.
//
// Runs a real loopback UDT data transfer: a server thread binds/listens/
// accepts while a client thread connects and sends a message; the server
// verifies the received bytes. Exercises startup/socket/bind/listen/accept/
// connect/send/recv/close/cleanup (R34: no empty-stub test).

#include <chrono>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <netdb.h>
#include <string>
#include <thread>

#include <sys/socket.h>
#include <netinet/in.h>

#include "udt.h"

static const char* kMsg = "UDT test_package hello from OHOS";
static const int kPort = 9000;

static std::mutex g_mtx;
static bool g_server_ready = false;
static int g_srv_rc = -1;
static int g_cli_rc = -1;

static int server_main() {
    addrinfo hints, *res = nullptr;
    std::memset(&hints, 0, sizeof(hints));
    hints.ai_flags = AI_PASSIVE;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    char service[16];
    std::snprintf(service, sizeof(service), "%d", kPort);
    if (getaddrinfo(nullptr, service, &hints, &res) != 0) return 1;

    UDTSOCKET serv = UDT::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (serv == UDT::INVALID_SOCK) { freeaddrinfo(res); return 1; }
    if (UDT::ERROR == UDT::bind(serv, res->ai_addr, res->ai_addrlen)) {
        freeaddrinfo(res);
        UDT::close(serv);
        return 1;
    }
    freeaddrinfo(res);
    if (UDT::ERROR == UDT::listen(serv, 16)) { UDT::close(serv); return 1; }

    {
        std::lock_guard<std::mutex> lk(g_mtx);
        g_server_ready = true;
    }

    sockaddr_storage caddr;
    int alen = sizeof(caddr);
    UDTSOCKET conn = UDT::accept(serv, (sockaddr*)&caddr, &alen);
    UDT::close(serv);
    if (conn == UDT::INVALID_SOCK) return 1;

    char rbuf[128];
    int need = (int)std::strlen(kMsg);
    int total = 0;
    while (total < need) {
        int r = UDT::recv(conn, rbuf + total, need - total, 0);
        if (r <= 0) { UDT::close(conn); return 1; }
        total += r;
    }
    rbuf[total] = '\0';
    UDT::close(conn);

    if (total != need || std::strcmp(rbuf, kMsg) != 0) {
        std::printf("UDT server data mismatch: got '%s'\n", rbuf);
        return 1;
    }
    return 0;
}

static int client_main() {
    // Wait for the server to be listening before connecting.
    for (int i = 0; i < 100; ++i) {
        {
            std::lock_guard<std::mutex> lk(g_mtx);
            if (g_server_ready) break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }

    addrinfo hints, *res = nullptr;
    std::memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    char service[16];
    std::snprintf(service, sizeof(service), "%d", kPort);
    if (getaddrinfo("127.0.0.1", service, &hints, &res) != 0) return 1;

    UDTSOCKET cli = UDT::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (cli == UDT::INVALID_SOCK) { freeaddrinfo(res); return 1; }
    if (UDT::ERROR == UDT::connect(cli, res->ai_addr, res->ai_addrlen)) {
        freeaddrinfo(res);
        UDT::close(cli);
        return 1;
    }
    freeaddrinfo(res);

    const char* data = kMsg;
    int need = (int)std::strlen(data);
    int sent = 0;
    while (sent < need) {
        int s = UDT::send(cli, data + sent, need - sent, 0);
        if (s <= 0) { UDT::close(cli); return 1; }
        sent += s;
    }
    UDT::close(cli);
    return (sent == need) ? 0 : 1;
}

int main() {
    if (UDT::ERROR == UDT::startup()) {
        std::printf("UDT startup() failed\n");
        return 1;
    }

    // server_main()/client_main() are ordinary int-returning functions; run
    // them in threads but capture their return values into the globals tested
    // below (a plain `std::thread srv(server_main)` silently discards the
    // return code and the FAILED check would always see the -1 initializers).
    std::thread srv([]() { g_srv_rc = server_main(); });
    std::thread cli([]() { g_cli_rc = client_main(); });
    srv.join();
    cli.join();

    UDT::cleanup();

    if (g_srv_rc != 0 || g_cli_rc != 0) {
        std::printf("UDT consumer test FAILED (server=%d client=%d)\n", g_srv_rc, g_cli_rc);
        return 1;
    }
    std::printf("UDT consumer test PASSED\n");
    return 0;
}
