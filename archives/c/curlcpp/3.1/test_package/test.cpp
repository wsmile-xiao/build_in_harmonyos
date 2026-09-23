#include <iostream>
#include <sstream>
#include <string>

#include "curlcpp/curl_easy.h"
#include "curlcpp/curl_form.h"
#include "curlcpp/curl_ios.h"
#include "curlcpp/curl_multi.h"
#include "curlcpp/curl_option.h"
#include "curlcpp/curl_pair.h"

static int s_passed = 0;
static int s_failed = 0;

#define CHECK(name, expr)                                     \
    do {                                                      \
        if (expr) {                                           \
            ++s_passed;                                       \
            std::cout << "PASS: " << name << std::endl;        \
        } else {                                              \
            ++s_failed;                                       \
            std::cout << "FAIL: " << name << std::endl;        \
        }                                                     \
    } while (0)

int main() {
    // 1. Default easy handle constructs without touching the network.
    try {
        curl::curl_easy easy;
        CHECK("easy_default_construct", easy.get_curl() != nullptr);
    } catch (...) {
        CHECK("easy_default_construct", false);
    }

    // 2. Setting transfer options is a local operation (no perform call).
    try {
        curl::curl_easy easy;
        easy.add<CURLOPT_URL>("http://example.com/");
        easy.add<CURLOPT_FOLLOWLOCATION>(1L);
        easy.add<CURLOPT_TIMEOUT>(10L);
        CHECK("easy_add_options", true);
    } catch (...) {
        CHECK("easy_add_options", false);
    }

    // 3. Stream-backed easy handle binds the output sink locally.
    try {
        std::ostringstream stream;
        curl::curl_ios<std::ostringstream> writer(stream);
        curl::curl_easy easy(writer);
        easy.add<CURLOPT_URL>("http://example.com/");
        CHECK("easy_stream_construct", easy.get_curl() != nullptr);
    } catch (...) {
        CHECK("easy_stream_construct", false);
    }

    // 4. Form fields compose locally without any transfer.
    try {
        curl::curl_form form;
        curl::curl_pair<CURLformoption, std::string> name(
            CURLFORM_COPYNAME, "user");
        curl::curl_pair<CURLformoption, std::string> content(
            CURLFORM_COPYCONTENTS, "curlcpp");
        form.add(name, content);
        CHECK("form_add_pair", true);
    } catch (...) {
        CHECK("form_add_pair", false);
    }

    // 5. Multi handle manages easy handles locally (no perform call).
    try {
        curl::curl_easy easy;
        easy.add<CURLOPT_URL>("http://example.com/");
        curl::curl_multi multi;
        multi.add(easy);
        const bool idle = (multi.get_active_transfers() == 0);
        multi.remove(easy);
        CHECK("multi_add_remove", idle && multi.get_curl() != nullptr);
    } catch (...) {
        CHECK("multi_add_remove", false);
    }

    // 6. Header-only option helper builds the expected option pair.
    try {
        const long timeout = 10L;
        const curl::curl_pair<CURLoption, long> opt =
            curl::make_option(CURLOPT_TIMEOUT, timeout);
        CHECK("make_option_pair",
              opt.first() == CURLOPT_TIMEOUT && opt.second() == timeout);
    } catch (...) {
        CHECK("make_option_pair", false);
    }

    std::cout << "RESULT: " << s_passed << " passed, " << s_failed
              << " failed" << std::endl;
    return s_failed == 0 ? 0 : 1;
}
