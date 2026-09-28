// test_easyhttpcpp.cpp — Substantive consumer test that calls the easyhttpcpp library API (R34).
// Constructs an EasyHttp client via Builder, builds Request objects, manipulates Headers
// and verifies observable values instead of only printing a string.

#include <easyhttpcpp/EasyHttp.h>
#include <easyhttpcpp/Headers.h>
#include <easyhttpcpp/Request.h>

#include <iostream>
#include <string>

namespace e = easyhttpcpp;

int main()
{
    int failures = 0;

    // --- Headers: set/get/remove round-trip ---
    e::Headers::Ptr pHeaders = new e::Headers();
    pHeaders->set("X-Test-Header", "easyhttpcpp");
    if (pHeaders->getValue("X-Test-Header", "") != "easyhttpcpp") {
        std::cerr << "FAIL: Headers.getValue() did not round-trip value" << std::endl;
        failures++;
    }
    if (pHeaders->getSize() < 1) {
        std::cerr << "FAIL: Headers.getSize() returned 0 after set" << std::endl;
        failures++;
    }
    std::cout << "PASS: Headers set/get round-trip, size=" << pHeaders->getSize() << std::endl;

    // --- Request::Builder: build a GET request and verify the URL ---
    e::Request::Builder reqBuilder;
    reqBuilder.httpGet().setUrl("http://127.0.0.1:1/path?q=1");
    e::Request::Ptr pRequest = reqBuilder.build();
    if (pRequest.isNull()) {
        std::cerr << "FAIL: Request::Builder.build() returned null" << std::endl;
        failures++;
    } else if (pRequest->getUrl() != "http://127.0.0.1:1/path?q=1") {
        std::cerr << "FAIL: Request.getUrl() mismatch: " << pRequest->getUrl() << std::endl;
        failures++;
    } else {
        std::cout << "PASS: Request built, url=" << pRequest->getUrl() << std::endl;
    }

    // --- EasyHttp::Builder: build a client instance (real constructor path) ---
    e::EasyHttp::Builder httpClientBuilder;
    e::EasyHttp::Ptr pHttpClient = httpClientBuilder.build();
    if (pHttpClient.isNull()) {
        std::cerr << "FAIL: EasyHttp::Builder.build() returned null" << std::endl;
        failures++;
    } else {
        unsigned int timeoutSec = pHttpClient->getTimeoutSec();
        std::cout << "PASS: EasyHttp client built, timeoutSec=" << timeoutSec << std::endl;
    }

    if (failures != 0) {
        std::cerr << "RESULT: " << failures << " failure(s)" << std::endl;
        return 1;
    }
    std::cout << "RESULT: ALL PASS" << std::endl;
    return 0;
}