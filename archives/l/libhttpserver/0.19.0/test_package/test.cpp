/* libhttpserver 0.19.0 —— 真实嵌入式 HTTP 服务起停+注册资源探针（非空壳）。
 *
 * 判据：create_webserver 监听固定高端口、注册资源、启动 daemon、
 * 本地 socket HTTP GET 请求并比对响应体、停止 daemon。
 * 覆盖 libhttpserver → libmicrohttpd(静态) → musl socket 全栈，桩实现过不了。
 * 端口策略：0.19.0 的 webserver 不暴露 get_port()（2.0.0 才有），用固定高端口
 * 45871（IANA 未分配区间，CI 环境无占用风险；本地跑若被占 kill 旧进程即可）。
 */
#include <httpserver.hpp>

#include <cstdio>
#include <cstring>
#include <string>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

class hello_resource : public httpserver::http_resource {
public:
    std::shared_ptr<httpserver::http_response> render(const httpserver::http_request&) override {
        return std::shared_ptr<httpserver::http_response>(
            new httpserver::string_response("hello from OHOS libhttpserver"));
    }
};

/* 最小阻塞 HTTP/1.1 GET 客户端（纯 POSIX socket，无 curl 依赖） */
static std::string http_get(uint16_t port) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return "";
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        ::close(fd);
        return "";
    }
    const char* req = "GET /hello HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if (::send(fd, req, strlen(req), 0) < 0) { ::close(fd); return ""; }
    std::string out;
    char buf[4096];
    for (;;) {
        ssize_t n = ::recv(fd, buf, sizeof(buf), 0);
        if (n <= 0) break;
        out.append(buf, static_cast<size_t>(n));
    }
    ::close(fd);
    return out;
}

int main() {
    const uint16_t port = 45871;
    try {
        hello_resource res;
        httpserver::webserver ws = httpserver::create_webserver(port)
            .max_threads(2);
        CHECK(ws.register_resource("/hello", &res), "register_resource(/hello)");

        ws.start(false);
        /* 0.19.0 API 语义：start(blocking=false) 固定返回 false（value_onclose 仅
         * blocking 模式为 true），非阻塞成功判定用 is_running()。 */
        CHECK(ws.is_running(), "webserver is_running after start (non-blocking)");

        std::string resp = http_get(port);
        CHECK(!resp.empty(), "HTTP GET received a response");
        CHECK(resp.find("200 OK") != std::string::npos, "status line 200 OK");
        CHECK(resp.find("hello from OHOS libhttpserver") != std::string::npos,
              "response body roundtrip");

        CHECK(ws.stop(), "webserver stop");
    } catch (const std::exception& e) {
        fprintf(stderr, "[FAIL] unexpected exception: %s\n", e.what());
        ++failures;
    }
    printf("%s: libhttpserver probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
