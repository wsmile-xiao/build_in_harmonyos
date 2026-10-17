// test_package for cinatra 0.8.9 — consumer smoke test on OHOS
//
// Starts a coro_http_server on 127.0.0.1 with GET/POST handlers,
// issues coro_http_client GET/POST requests against it (full loopback
// round trip), and checks status codes + body. Exercises the vendored
// asio + async_simple coroutine stack end-to-end including the patched
// coro_io::io_context_pool (both cpu_affinity=false and true, the
// latter covering the portable sched_setaffinity(0, ...) branch).
#include <cinatra/coro_http_server.hpp>
#include <cinatra/coro_http_client.hpp>

#include <cstdio>
#include <string>

static int run_server(bool cpu_affinity) {
    using namespace cinatra;

    // cpu_affinity=true exercises the patched sched_setaffinity(0, ...)
    // worker-thread pinning path in coro_io::io_context_pool.
    coro_http_server server(cpu_affinity ? 2 : 1, 18080, cpu_affinity);
    server.set_http_handler<GET>(
        "/",
        [](coro_http_request &req, coro_http_response &resp) {
            resp.set_status_and_content(status_type::ok,
                                        "hello cinatra on ohos");
        });
    server.set_http_handler<POST>(
        "/echo",
        [](coro_http_request &req, coro_http_response &resp) {
            std::string body(req.get_body());
            resp.set_status_and_content(status_type::ok, std::move(body));
        });
    auto fut = server.async_start();
    if (server.port() == 0) {
        std::fprintf(stderr, "FAIL: server did not pick a port\n");
        return 1;
    }
    // async_start future: a ready future carrying a non-zero errc means the
    // listen() step failed immediately; still-pending means the server is
    // accepting connections as expected.
    if (fut.hasResult() && fut.value() != std::errc{}) {
        std::fprintf(stderr, "FAIL: server listen failed\n");
        return 1;
    }

    coro_http_client client;
    resp_data result = client.get("http://127.0.0.1:18080/");
    if (result.net_err) {
        std::fprintf(stderr, "FAIL: client get error: %s\n",
                     result.net_err.message().c_str());
        server.stop();
        return 1;
    }
    if (result.status != 200 || result.resp_body != "hello cinatra on ohos") {
        std::fprintf(stderr, "FAIL: GET status=%d\n", (int)result.status);
        server.stop();
        return 1;
    }
    std::printf("[%s] GET / -> %d %.*s\n", cpu_affinity ? "affinity" : "plain",
                (int)result.status, (int)result.resp_body.size(),
                result.resp_body.data());

    // POST round trip: server echoes the request body back
    resp_data result2 = client.post("http://127.0.0.1:18080/echo",
                                    "ping-ohos", req_content_type::text);
    if (result2.net_err || result2.status != 200 ||
        result2.resp_body != "ping-ohos") {
        std::fprintf(stderr, "FAIL: POST round trip (status=%d)\n",
                     (int)result2.status);
        server.stop();
        return 1;
    }
    std::printf("[%s] POST /echo -> %d %.*s\n",
                cpu_affinity ? "affinity" : "plain", (int)result2.status,
                (int)result2.resp_body.size(), result2.resp_body.data());

    server.stop();
    return 0;
}

int main() {
    if (run_server(false) != 0) return 1;  // default path (cpu_affinity=false)
    if (run_server(true) != 0) return 1;   // sched_setaffinity(0,...) path
    std::printf("test_package PASSED\n");
    return 0;
}
