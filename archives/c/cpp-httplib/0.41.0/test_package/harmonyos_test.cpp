#ifndef __OHOS__
#error "This test must be compiled with the HarmonyOS toolchain"
#endif

#if !defined(__aarch64__) && !defined(_M_ARM64)
#error "This HarmonyOS PC validation targets aarch64"
#endif

#include <httplib.h>

#include <sys/utsname.h>

#include <cstring>
#include <iostream>
#include <string>

int main()
{
    struct utsname system_info {};
    if (uname(&system_info) != 0) {
        std::cerr << "uname failed" << std::endl;
        return 1;
    }
    const std::string machine = system_info.machine;
    if (machine != "aarch64" && machine != "arm64") {
        std::cerr << "unexpected HarmonyOS machine: " << machine << std::endl;
        return 2;
    }
    if (std::strcmp(CPPHTTPLIB_VERSION, "0.41.0") != 0) {
        std::cerr << "unexpected cpp-httplib version: " << CPPHTTPLIB_VERSION
                  << std::endl;
        return 3;
    }

    httplib::detail::UrlComponents url;
    if (!httplib::detail::parse_url(
            "http://127.0.0.1:8080/harmonyos?arch=aarch64", url)) {
        return 4;
    }
    if (url.scheme != "http" || url.host != "127.0.0.1" ||
        url.port != "8080" || url.path != "/harmonyos" ||
        url.query != "?arch=aarch64") {
        return 5;
    }

    httplib::Response response;
    response.status = 200;
    response.set_header("X-Platform", "HarmonyOS");
    response.set_content("ohos-api-ok:" + machine, "text/plain");
    if (response.status != 200 ||
        response.body != "ohos-api-ok:" + machine ||
        response.get_header_value("X-Platform") != "HarmonyOS" ||
        response.get_header_value("Content-Type") != "text/plain") {
        return 6;
    }

    std::cout << "HARMONYOS_CPP_HTTPLIB_TEST_OK arch=" << machine
              << " kernel="
              << system_info.release << " version=" << CPPHTTPLIB_VERSION
              << std::endl;
    return 0;
}
