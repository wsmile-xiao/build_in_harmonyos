// Consumer test for psocksxx: real TCP echo round-trip through the public
// API. A loopback echo server runs in a std::thread on 127.0.0.1:<ephemeral>;
// the consumer connects with psocksxx::tcpnsockstream, writes a line and
// asserts the echoed bytes come back through the stream interface.
#include <psocksxx/nsockaddr.h>
#include <psocksxx/tcpnsockstream.h>

#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

int g_listen_fd = -1;

void echo_server() {
    int client = accept(g_listen_fd, NULL, NULL);
    if (client < 0) {
        return;
    }
    char buf[256];
    ssize_t n;
    while ((n = recv(client, buf, sizeof(buf), 0)) > 0) {
        ssize_t off = 0;
        while (off < n) {
            ssize_t w = send(client, buf + off, static_cast<size_t>(n - off), 0);
            if (w <= 0) {
                close(client);
                return;
            }
            off += w;
        }
    }
    close(client);
}

}  // namespace

int main() {
    g_listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (g_listen_fd < 0) {
        std::fprintf(stderr, "socket: %s\n", std::strerror(errno));
        return 2;
    }
    struct sockaddr_in addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(g_listen_fd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
        std::fprintf(stderr, "bind: %s\n", std::strerror(errno));
        return 2;
    }
    socklen_t addrlen = sizeof(addr);
    if (getsockname(g_listen_fd, reinterpret_cast<struct sockaddr*>(&addr), &addrlen) < 0) {
        std::fprintf(stderr, "getsockname: %s\n", std::strerror(errno));
        return 2;
    }
    if (listen(g_listen_fd, 1) < 0) {
        std::fprintf(stderr, "listen: %s\n", std::strerror(errno));
        return 2;
    }
    const unsigned short port = ntohs(addr.sin_port);

    std::thread server(echo_server);

    const char message[] = "hello psocksxx";
    try {
        psocksxx::tcpnsockstream stream;
        psocksxx::nsockaddr addr("127.0.0.1", port);
        stream.connect(&addr);
        for (const char* p = message; *p; ++p) {
            stream << *p;
        }
        stream << std::endl;

        std::string echoed;
        std::getline(stream, echoed);
        if (echoed != message) {
            std::fprintf(stderr, "echo mismatch: got \"%s\"\n", echoed.c_str());
            return 1;
        }
    } catch (psocksxx::sockexception& e) {
        std::fprintf(stderr, "sockexception: %s\n", e.what());
        return 1;
    }

    close(g_listen_fd);
    server.join();
    std::printf("psocksxx consumer echo round-trip OK\n");
    return 0;
}
