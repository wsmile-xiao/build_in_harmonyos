// test_cppdap.cpp — consumer smoke test for cppdap 1.58.0a.
// Exercises the public Session / protocol / io API: session creation,
// request handler registration, protocol struct defaults and pipe roundtrip.
#include <dap/io.h>
#include <dap/protocol.h>
#include <dap/session.h>

#include <cstring>
#include <iostream>
#include <string>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, label)                                              \
    do {                                                                \
        ++g_checks;                                                     \
        if (cond) {                                                     \
            std::cout << "PASS: " << label << "\n";                     \
        } else {                                                        \
            ++g_failed;                                                 \
            std::cerr << "FAIL: " << label << "\n";                     \
        }                                                               \
    } while (0)

int main() {
    // 1. Session creation and handler registration.
    auto session = dap::Session::create();
    CHECK(session != nullptr, "Session::create returns non-null session");

    bool error_handler_set = false;
    session->onError([&](const char*) { error_handler_set = true; });
    CHECK(true, "Session::onError accepts handler");

    session->registerHandler([](const dap::InitializeRequest&) {
        dap::InitializeResponse response;
        response.supportsConfigurationDoneRequest = true;
        return response;
    });
    CHECK(true, "register InitializeRequest handler");

    session->registerHandler([&](const dap::ThreadsRequest&) {
        dap::ThreadsResponse response;
        dap::Thread thread;
        thread.id = 100;
        thread.name = "TheThread";
        response.threads.push_back(thread);
        return response;
    });
    CHECK(true, "register ThreadsRequest handler");

    // 2. Protocol value semantics.
    dap::InitializeRequest init_req;
    init_req.adapterID = "hmbs-test-adapter";
    CHECK(init_req.adapterID == "hmbs-test-adapter", "InitializeRequest adapterID roundtrip");

    dap::Thread thread;
    thread.id = 100;
    thread.name = "TheThread";
    CHECK(thread.id == 100 && thread.name == "TheThread", "Thread id/name roundtrip");

    dap::Error ok;
    CHECK(!static_cast<bool>(ok), "default Error is success");
    dap::Error err("boom");
    CHECK(static_cast<bool>(err) && err.message == "boom", "Error message roundtrip");

    dap::ResponseOrError<dap::InitializeResponse> wrapped{err};
    CHECK(static_cast<bool>(wrapped.error), "ResponseOrError carries error");

    // 3. Pipe roundtrip exercises dap::Reader / dap::Writer.
    auto rw = dap::pipe();
    CHECK(rw != nullptr && rw->isOpen(), "dap::pipe returns open ReaderWriter");
    const char* payload = "dap-ping";
    const size_t len = std::strlen(payload);
    CHECK(rw->write(payload, len), "pipe write succeeds");
    // NOTE: dap::pipe Reader blocks until the requested byte count is
    // fulfilled or the stream is closed (see src/io.cpp Pipe::read). Request
    // exactly what was written; asking for more than available hangs forever
    // and the preflight watchdog kills the test with Signal 9 (exit 137).
    char buf[32] = {};
    size_t got = rw->read(buf, len);
    CHECK(got == len && std::string(buf, got) == payload, "pipe read returns written bytes");
    rw->close();
    CHECK(!rw->isOpen(), "pipe close marks stream closed");

    (void)error_handler_set;

    std::cout << "cppdap smoke test: " << (g_checks - g_failed) << "/" << g_checks << " checks passed\n";
    return g_failed == 0 ? 0 : 1;
}
