// test_package: real consumer of the installed coeurl public API.
//
// Spawns an in-process mini HTTP server (raw socket + thread, listens on
// 127.0.0.1:18080) and drives the installed coeurl::Client through its
// public async GET API against it. Verifies url/status/body/content-type
// per request (4 assertions x 3 requests), then relies on the Client
// destructor to exercise the libevent/curl teardown path.
#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <functional>
#include <mutex>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>
#include <thread>
#include <unistd.h>
#include <vector>

#include <coeurl/client.hpp>
#include <coeurl/request.hpp>

namespace {

// ---------------------------------------------------------------- //
// mini HTTP server                                                  //
// ---------------------------------------------------------------- //

int g_listen_fd = -1;

bool write_all(int fd, const char *buf, size_t len) {
    size_t off = 0;
    while (off < len) {
        ssize_t n = ::send(fd, buf + off, len - off, 0);
        if (n <= 0) {
            return false;
        }
        off += static_cast<size_t>(n);
    }
    return true;
}

// Parse "GET <path> HTTP/1.x" from the request head.
bool parse_request_line(const std::string &head, std::string &method,
                        std::string &path) {
    const size_t sp1 = head.find(' ');
    if (sp1 == std::string::npos) {
        return false;
    }
    const size_t sp2 = head.find(' ', sp1 + 1);
    if (sp2 == std::string::npos) {
        return false;
    }
    method = head.substr(0, sp1);
    path = head.substr(sp1 + 1, sp2 - sp1 - 1);
    return true;
}

void respond(int fd, const std::string &path) {
    std::string body;
    std::string ctype = "text/plain; charset=utf-8";
    if (path == "/") {
        body = "OK";
    } else if (path == "/data") {
        body = "coeurl-ohos";
    } else {
        const char *not_found =
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n"
            "\r\n";
        write_all(fd, not_found, std::strlen(not_found));
        return;
    }

    const std::string resp =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: " + ctype + "\r\n"
        "Content-Length: " + std::to_string(body.size()) + "\r\n"
        "Connection: close\r\n"
        "\r\n" + body;
    write_all(fd, resp.data(), resp.size());
}

void http_server(std::atomic<bool> &stop) {
    while (!stop.load()) {
        const int conn = ::accept(g_listen_fd, nullptr, nullptr);
        if (conn < 0) {
            if (stop.load()) {
                break;
            }
            continue;
        }
        std::string buf;
        char chunk[1024];
        for (;;) {
            const ssize_t n = ::recv(conn, chunk, sizeof(chunk), 0);
            if (n <= 0) {
                break;
            }
            buf.append(chunk, static_cast<size_t>(n));
            const size_t head_end = buf.find("\r\n\r\n");
            if (head_end != std::string::npos) {
                std::string method;
                std::string path;
                if (parse_request_line(buf, method, path) && method == "GET") {
                    respond(conn, path);
                } else {
                    const char *bad =
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Length: 0\r\n"
                        "Connection: close\r\n"
                        "\r\n";
                    write_all(conn, bad, std::strlen(bad));
                }
                break;
            }
        }
        ::close(conn);
    }
}

// ---------------------------------------------------------------- //
// tiny assertion helper                                             //
// ---------------------------------------------------------------- //

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char *what, const std::string &got,
           const std::string &expected) {
    g_checks++;
    if (ok) {
        std::printf("PASS (%d): %s\n", g_checks, what);
    } else {
        g_failures++;
        std::printf("FAIL (%d): %s — got [%s], expected [%s]\n", g_checks,
                    what, got.c_str(), expected.c_str());
    }
}

void check(int got, int expected, const char *what) {
    check(got == expected, what, std::to_string(got),
          std::to_string(expected));
}

} // namespace

int main() {
    // watchdog: never let a hung event loop block CI forever
    std::thread watchdog([]() {
        std::this_thread::sleep_for(std::chrono::seconds(120));
        std::printf("FAIL: watchdog timeout (120s) — aborting\n");
        std::fflush(stdout);
        _exit(2);
    });
    watchdog.detach();

    g_listen_fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (g_listen_fd < 0) {
        std::printf("FAIL: socket() failed: %s\n", std::strerror(errno));
        return 2;
    }
    int reuse = 1;
    ::setsockopt(g_listen_fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(18080);
    if (::bind(g_listen_fd, reinterpret_cast<struct sockaddr *>(&addr),
               sizeof(addr)) != 0) {
        std::printf("FAIL: bind() failed: %s\n", std::strerror(errno));
        return 2;
    }
    if (::listen(g_listen_fd, 8) != 0) {
        std::printf("FAIL: listen() failed: %s\n", std::strerror(errno));
        return 2;
    }

    std::atomic<bool> stop{false};
    std::thread server(http_server, std::ref(stop));

    {
        // Client scope: the destructor must join the event thread cleanly
        // after all requests completed (libevent/curl teardown path).
        coeurl::Client client{};

        std::mutex done_mutex;
        std::condition_variable done_cv;
        int completed = 0;

        auto base = std::string("http://127.0.0.1:18080");
        const std::vector<std::string> targets = {"/", "/data", "/"};
        const std::vector<std::string> bodies = {"OK", "coeurl-ohos", "OK"};

        for (size_t i = 0; i < targets.size(); i++) {
            client.get(base + targets[i],
                       [&completed, &done_mutex, &done_cv, &targets, &bodies,
                        &base, i](const coeurl::Request &r) {
                           check(std::string(r.url()) == base + targets[i],
                                 "url()", std::string(r.url()),
                                 base + targets[i]);
                           check(r.response_code(), 200, "response_code()");
                           check(std::string(r.response()) == bodies[i],
                                 "response()", std::string(r.response()),
                                 bodies[i]);
                           check(
                               std::string(
                                   r.response_headers()["content-type"]) ==
                                   "text/plain; charset=utf-8",
                               "content-type header",
                               std::string(
                                   r.response_headers()["content-type"]),
                               "text/plain; charset=utf-8");
                           std::lock_guard<std::mutex> lock(done_mutex);
                           completed++;
                           done_cv.notify_one();
                       });
        }

        std::unique_lock<std::mutex> lock(done_mutex);
        const bool all = done_cv.wait_for(lock, std::chrono::seconds(60),
                                          [&completed]() {
                                              return completed == 3;
                                          });
        check(all && completed == 3, "all requests completed",
              std::to_string(completed), "3");
    }

    stop.store(true);
    ::shutdown(g_listen_fd, SHUT_RDWR);
    ::close(g_listen_fd);
    server.join();

    std::printf("checks=%d failures=%d\n", g_checks, g_failures);
    if (g_failures == 0 && g_checks == 13) {
        std::printf("COEURL_TEST_PACKAGE_OK\n");
        return 0;
    }
    return 1;
}
