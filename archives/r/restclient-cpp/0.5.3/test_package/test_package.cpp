// Consumer test for restclient-cpp: built only against the installed package,
// driving the public API over loopback HTTP and asserting on returned state.
#include "restclient-cpp/restclient.h"
#include "restclient-cpp/connection.h"
#include "restclient-cpp/version.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cctype>
#include <iostream>
#include <string>

namespace {

int checks = 0;
int failures = 0;

void expect(bool passed, const std::string& description)
{
    ++checks;
    if (passed) {
        std::cout << "ok   - " << description << std::endl;
        return;
    }
    ++failures;
    std::cout << "FAIL - " << description << std::endl;
}

bool contains(const std::string& haystack, const std::string& needle)
{
    return haystack.find(needle) != std::string::npos;
}

// HeaderFields keeps response headers keyed exactly as the server sent them, so
// a consumer that cares about a standard header has to fold case itself.
bool has_header(const RestClient::HeaderFields& headers, const std::string& name)
{
    auto fold = [](const std::string& value) {
        std::string folded = value;
        for (char& c : folded) {
            c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        }
        return folded;
    };
    const std::string wanted = fold(name);
    for (const auto& entry : headers) {
        if (fold(entry.first) == wanted) {
            return true;
        }
    }
    return false;
}

// A port that was bound and released has no listener, which is what the
// transport-error case needs.
std::string closed_port()
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return "1";
    }
    sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0;
    if (bind(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
        close(fd);
        return "1";
    }
    socklen_t len = sizeof(address);
    if (getsockname(fd, reinterpret_cast<sockaddr*>(&address), &len) != 0) {
        close(fd);
        return "1";
    }
    int port = ntohs(address.sin_port);
    close(fd);
    return std::to_string(port);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc < 2) {
        std::cerr << "usage: test_package <base-url>" << std::endl;
        return 2;
    }
    const std::string base = argv[1];

    if (RestClient::init() != 0) {
        std::cerr << "RestClient::init() failed" << std::endl;
        return 1;
    }

    expect(std::string(RESTCLIENT_VERSION) == "0.5.3",
           "installed version header reports 0.5.3");

    RestClient::Response got = RestClient::get(base + "/index.json");
    expect(got.code == 200, "free function GET returns 200");
    expect(contains(got.body, "\"library\": \"restclient-cpp\""),
           "GET body carries the served document");
    expect(has_header(got.headers, "Content-Type"),
           "response header map holds the served Content-Type");

    RestClient::Response missing = RestClient::get(base + "/absent.json");
    expect(missing.code == 404, "free function GET maps a missing path to 404");

    RestClient::Response head = RestClient::head(base + "/index.json");
    expect(head.code == 200 && head.body.empty(),
           "HEAD returns status without a body");

    RestClient::Response refused = RestClient::post(base + "/index.json",
                                                   "application/json", "{}");
    expect(refused.code == 501 && contains(refused.body, "Unsupported method"),
           "POST surfaces the server's 501 error page as the response body");

    RestClient::Connection connection(base);
    RestClient::HeaderFields headers;
    headers["X-Consumer-Test"] = "restclient-cpp";
    connection.SetHeaders(headers);
    connection.SetTimeout(10);
    expect(connection.GetHeaders().count("X-Consumer-Test") == 1,
           "SetHeaders is reflected by GetHeaders");

    RestClient::Connection::Info configured = connection.GetInfo();
    expect(configured.headers.count("X-Consumer-Test") == 1,
           "GetInfo reports the configured custom header");
    expect(configured.timeout == 10, "GetInfo reports the configured timeout");

    RestClient::Response via_connection = connection.get("/index.json");
    expect(via_connection.code == 200,
           "Connection GET reaches the same document");
    RestClient::Connection::Info after = connection.GetInfo();
    expect(after.lastRequest.curlCode == 0, "last request had no libcurl error");
    expect(after.lastRequest.totalTime > 0, "last request recorded elapsed time");

    RestClient::Connection unreachable("http://127.0.0.1:" + closed_port());
    unreachable.SetTimeout(5);
    RestClient::Response failed = unreachable.get("/");
    expect(failed.code == CURLE_COULDNT_CONNECT,
           "a listener-less port yields CURLE_COULDNT_CONNECT");
    // curl >= 8 reworded the CURLE_COULDNT_CONNECT string; what the consumer
    // relies on is that the libcurl message for that code reaches the body.
    expect(failed.body == "Couldn't connect to server" ||
           failed.body == "Could not connect to server",
           "the libcurl error string reaches the response body");

    RestClient::disable();

    std::cout << checks - failures << "/" << checks
              << " consumer assertions passed" << std::endl;
    return failures == 0 ? 0 : 1;
}
