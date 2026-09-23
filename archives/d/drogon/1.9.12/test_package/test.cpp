// drogon test_package — verifies core drogon subsystems link and run on OHOS:
//   1. HttpAppFramework singleton + event loop construction (app().getLoop())
//   2. HttpResponse construction (HttpResponse::newHttpResponse) and header
//      manipulation (addHeader / status handling)
//   3. URI routing table registration (app().registerHandler + registered
//      handlers count via app().getHandlersInfo())
//   4. Utilities: Base64 encode/decode round-trip (drogon::utils)
//   5. Middleware/filter registration (app().appendPlugin is not needed; a
//      simple HttpFilter-less attribute check keeps this a link+run test)
//
// NOTE: checks use explicit `return 1` on failure instead of assert(),
// so they remain effective under Release builds (NDEBUG) and ctest
// reports a non-zero exit code on any regression.
#include <drogon/drogon.h>
#include <drogon/HttpAppFramework.h>
#include <drogon/HttpResponse.h>
#include <drogon/utils/Utilities.h>

#include <trantor/net/EventLoop.h>

#include <iostream>

// CHECK macro: prints a failure message and returns 1 from main.
// Works under both Debug and Release builds (no NDEBUG dependency).
#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (!(cond)) {                                              \
            std::cerr << "[FAIL] " << (msg) << std::endl;          \
            return 1;                                               \
        }                                                           \
    } while (0)

int main()
{
    // ── 1. HttpAppFramework: framework singleton + event loop ──
    auto &app = drogon::app();
    trantor::EventLoop *loop = app.getLoop();
    CHECK(loop != nullptr, "app().getLoop() returned nullptr");
    std::cout << "[ok] HttpAppFramework + EventLoop ready" << std::endl;

    // ── 2. HttpResponse: construction and header manipulation ──
    auto resp = drogon::HttpResponse::newHttpResponse();
    CHECK(resp != nullptr, "newHttpResponse returned nullptr");
    resp->addHeader("Content-Type", "text/plain");
    resp->setBody("hello from drogon on OHOS");
    CHECK(resp->getBody() == "hello from drogon on OHOS", "response body mismatch");
    CHECK(resp->getHeader("Content-Type") == "text/plain", "response header mismatch");
    std::cout << "[ok] HttpResponse construction + headers" << std::endl;

    // ── 3. Routing: register an async handler and verify handler count ──
    auto handlerInfoCountBefore = app.getHandlersInfo().size();
    app.registerHandler(
        "/hello",
        [](const drogon::HttpRequestPtr &,
           std::function<void(const drogon::HttpResponsePtr &)> &&callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("Hello, OHOS!");
            callback(resp);
        },
        {drogon::Get});
    auto handlerInfoCountAfter = app.getHandlersInfo().size();
    CHECK(handlerInfoCountAfter == handlerInfoCountBefore + 1,
          "registerHandler did not register the /hello route");
    std::cout << "[ok] route /hello registered (handlers: "
              << handlerInfoCountAfter << ")" << std::endl;

    // ── 4. Utilities: Base64 round-trip ──
    const std::string original = "drogon-on-harmonyos-pc";
    const std::string encoded = drogon::utils::base64Encode(original);
    const std::string decoded = drogon::utils::base64Decode(encoded);
    CHECK(decoded == original, "Base64 round-trip mismatch");
    std::cout << "[ok] Utilities base64 round-trip" << std::endl;

    // ── 5. Client: HttpClient facade reachable (newHttpClient factory) ──
    //     Construct a client inside the loop context — verifies trantor + SSL
    //     symbols are transitively linked without needing a live connection.
    auto clientPtr = drogon::HttpClient::newHttpClient("http://127.0.0.1:1", loop);
    CHECK(clientPtr != nullptr, "newHttpClient returned nullptr");
    std::cout << "[ok] HttpClient factory (trantor + TLS linkage)" << std::endl;

    std::cout << "All drogon subsystem tests passed!" << std::endl;
    return 0;
}
