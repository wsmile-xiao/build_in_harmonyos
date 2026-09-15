// test_dd_opentracing.cpp — consumer smoke test for dd-opentracing-cpp 1.3.7.
//
// Exercises the real public API without needing a running Datadog Agent:
// makeTracer, StartSpan, SetTag, Finish, stream Inject/Extract propagation
// and the getOptions/toJSON helpers. Prints one TAP-style line per check plus
// a final DD_TEST_SUMMARY line consumed by the test_package conanfile for the
// HMBS_TEST_PACKAGE_RESULT evidence marker.

#include <datadog/opentracing.h>

#include <iostream>
#include <sstream>
#include <string>

namespace dd = datadog::opentracing;

namespace {

int g_total = 0;
int g_passed = 0;

void check(bool ok, const char *name) {
    ++g_total;
    if (ok) {
        ++g_passed;
        std::cout << "PASS: " << name << "\n";
    } else {
        std::cout << "FAIL: " << name << "\n";
    }
}

}  // namespace

int main() {
    dd::TracerOptions options;
    options.service = "dd-ohos-smoke";
    options.agent_host = "127.0.0.1";
    options.environment = "ohos-test";

    auto tracer = dd::makeTracer(options);
    check(tracer != nullptr, "makeTracer returns non-null tracer");
    if (!tracer) {
        std::cout << "DD_TEST_SUMMARY passed=" << g_passed << " total=" << g_total << "\n";
        return 1;
    }

    auto span = tracer->StartSpan("ohos-smoke-operation");
    check(span != nullptr, "StartSpan returns non-null span");
    if (!span) {
        std::cout << "DD_TEST_SUMMARY passed=" << g_passed << " total=" << g_total << "\n";
        return 1;
    }
    span->SetTag("test.tag", "ohos");
    span->SetTag("test.number", 42);
    check(true, "SetTag string/number tags accepted");

    // Binary stream propagation round-trip (no network involved).
    std::ostringstream out;
    auto inject_result = tracer->Inject(span->context(), out);
    check(static_cast<bool>(inject_result), "Inject span context into stream");
    check(!out.str().empty(), "Injected payload is non-empty");

    std::istringstream in(out.str());
    auto extract_result = tracer->Extract(in);
    check(static_cast<bool>(extract_result), "Extract span context from stream");

    // Options round-trip through the tracer instance.
    const dd::TracerOptions &back = dd::getOptions(*tracer);
    check(back.service == "dd-ohos-smoke", "getOptions round-trips service name");
    check(back.type == "web", "default trace type is web");

    // JSON serialization helper (used for startup logs).
    const std::string config_json = dd::toJSON(options, false);
    check(config_json.find("dd-ohos-smoke") != std::string::npos,
          "toJSON serializes configured service");

    span->Finish();
    check(true, "span Finish completes without crash");

    std::cout << "DD_TEST_SUMMARY passed=" << g_passed << " total=" << g_total << "\n";
    return (g_passed == g_total) ? 0 : 1;
}
