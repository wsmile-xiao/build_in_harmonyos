#include <httplib.h>

#include <chrono>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

int main()
{
    if (std::strcmp(CPPHTTPLIB_VERSION, "0.41.0") != 0) {
        std::cerr << "unexpected cpp-httplib version: " << CPPHTTPLIB_VERSION
                  << std::endl;
        return 1;
    }

    httplib::detail::UrlComponents url;
    if (!httplib::detail::parse_url("http://127.0.0.1:8080/echo?value=harmony", url)) {
        return 2;
    }
    if (url.scheme != "http" || url.host != "127.0.0.1" ||
        url.port != "8080" || url.path != "/echo" ||
        url.query != "?value=harmony") {
        return 3;
    }

    httplib::Server server;
    server.Get("/echo", [](const httplib::Request &request, httplib::Response &response) {
        const auto value = request.get_param_value("value");
        response.set_header("X-Test-Package", "cpp-httplib-0.41.0");
        response.set_content("echo:" + value, "text/plain");
    });
    server.Post("/submit", [](const httplib::Request &request,
                              httplib::Response &response) {
        response.set_header("X-Request-Size", std::to_string(request.body.size()));
        response.set_content("accepted:" + request.body, "text/plain");
    });

    const int port = server.bind_to_any_port("127.0.0.1");
    if (port <= 0) {
        std::cerr << "failed to bind a loopback port" << std::endl;
        return 4;
    }

    std::thread server_thread([&server] { server.listen_after_bind(); });
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    httplib::Client client("127.0.0.1", port);
    const auto get_result = client.Get("/echo?value=harmony");
    const auto post_result = client.Post("/submit", "payload", "text/plain");

    server.stop();
    server_thread.join();

    if (!get_result) return 5;
    if (get_result->status != 200) return 6;
    if (get_result->body != "echo:harmony") return 7;
    if (get_result->get_header_value("Content-Type") != "text/plain") return 8;
    if (get_result->get_header_value("X-Test-Package") !=
        "cpp-httplib-0.41.0") return 9;
    if (!post_result) return 10;
    if (post_result->status != 200) return 11;
    if (post_result->body != "accepted:payload") return 12;
    if (post_result->get_header_value("X-Request-Size") != "7") return 13;

    std::cout << "CPP_HTTPLIB_CONSUMER_TEST_OK version=" << CPPHTTPLIB_VERSION
              << " get=200 post=200"
              << std::endl;
    return 0;
}
