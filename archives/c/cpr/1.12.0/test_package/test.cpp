// test_package for cpr 1.12.0 — substantively exercises the cpr API.
//
// Starts a minimal HTTP server on a localhost ephemeral port, performs a real
// cpr::Get against it, and asserts the HTTP status code and body. This runs the
// actual cpr library + libcurl backend (R34: no empty-shell test).

#include <cpr/cpr.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

namespace {

constexpr const char* kBody = "<html>cpr-test-ok</html>";

struct ServerInfo {
    int port = -1;
    std::atomic<bool> started{false};
};

void RunHttpServer(ServerInfo& info) {
    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        std::perror("socket");
        return;
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;  // ephemeral port
    if (bind(listen_fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        std::perror("bind");
        close(listen_fd);
        return;
    }
    socklen_t len = sizeof(addr);
    if (getsockname(listen_fd, reinterpret_cast<sockaddr*>(&addr), &len) != 0) {
        std::perror("getsockname");
        close(listen_fd);
        return;
    }
    info.port = ntohs(addr.sin_port);
    info.started.store(true);

    if (listen(listen_fd, 1) != 0) {
        std::perror("listen");
        close(listen_fd);
        return;
    }
    int client_fd = accept(listen_fd, nullptr, nullptr);
    if (client_fd < 0) {
        std::perror("accept");
        close(listen_fd);
        return;
    }
    char buf[4096];
    (void)::recv(client_fd, buf, sizeof(buf), 0);

    std::string response = "HTTP/1.1 200 OK\r\n"
                           "Content-Type: text/html\r\n"
                           "Content-Length: " +
                           std::to_string(std::strlen(kBody)) +
                           "\r\n"
                           "Connection: close\r\n"
                           "\r\n" +
                           kBody;
    (void)::send(client_fd, response.data(), response.size(), 0);
    close(client_fd);
    close(listen_fd);
}

}  // namespace

int main() {
    ServerInfo info;
    std::thread server(RunHttpServer, std::ref(info));
    while (!info.started.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    if (info.port < 0) {
        std::fprintf(stderr, "FAIL: server failed to start\n");
        server.join();
        return 1;
    }

    const std::string url = "http://127.0.0.1:" + std::to_string(info.port) + "/";
    cpr::Response r = cpr::Get(cpr::Url{url});

    server.join();

    if (r.status_code != 200) {
        std::fprintf(stderr, "FAIL: cpr::Get status=%ld url=%s\n",
                     r.status_code, url.c_str());
        return 1;
    }
    if (r.text.find("cpr-test-ok") == std::string::npos) {
        std::fprintf(stderr, "FAIL: unexpected body: %s\n", r.text.c_str());
        return 1;
    }

    std::printf("test_cpr OK: GET %s -> %ld, body=%s\n",
                url.c_str(), r.status_code, r.text.c_str());
    return 0;
}
