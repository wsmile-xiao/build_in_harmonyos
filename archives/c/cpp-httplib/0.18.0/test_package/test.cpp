#include <httplib.h>
#include <thread>
#include <chrono>
#include <iostream>

// 实质 HTTP 往返验证：本地起一个 Server，用 Client 发起 GET，
// 验证响应内容与状态码（R34：必须实际调用被测包 API，非空壳打印）
int main() {
    httplib::Server svr;
    svr.Get("/ping", [](const httplib::Request &, httplib::Response &res) {
        res.set_content("pong", "text/plain");
    });

    int port = svr.bind_to_any_port("127.0.0.1");
    if (port <= 0) {
        std::cerr << "FAIL: could not obtain bound port" << std::endl;
        return 1;
    }

    std::thread th([&]() { svr.listen_after_bind(); });
    std::this_thread::sleep_for(std::chrono::milliseconds(300));

    httplib::Client cli("127.0.0.1", port);
    if (auto res = cli.Get("/ping")) {
        if (res->status != 200) {
            std::cerr << "FAIL: expected 200, got " << res->status << std::endl;
            th.join();
            return 1;
        }
        if (res->body != "pong") {
            std::cerr << "FAIL: expected body 'pong', got '" << res->body << "'" << std::endl;
            th.join();
            return 1;
        }
        std::cout << "cpp-httplib test PASSED: GET /ping -> 200 'pong'" << std::endl;
    } else {
        auto err = res.error();
        std::cerr << "FAIL: request failed, error=" << httplib::to_string(err) << std::endl;
        th.join();
        return 1;
    }

    svr.stop();
    th.join();
    return 0;
}