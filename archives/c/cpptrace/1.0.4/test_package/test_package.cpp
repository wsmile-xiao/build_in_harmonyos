#include <cpptrace/cpptrace.hpp>
#include <cpptrace/version.hpp>
#include <iostream>
#include <string>

// Verify basic library linkage and object API without relying on runtime
// unwinding (guarded separately by test_ohos.cpp).
int main() {
    std::cout << "cpptrace version: "
              << CPPTRACE_VERSION_MAJOR << "." << CPPTRACE_VERSION_MINOR
              << "." << CPPTRACE_VERSION_PATCH << std::endl;

    cpptrace::stacktrace empty_trace;
    const std::string empty_rendered = empty_trace.to_string();
    // An empty trace renders a header line but no numbered frames.
    if (empty_rendered.find("#0") != std::string::npos) {
        std::cerr << "unexpected frame in empty trace: " << empty_rendered << std::endl;
        return 1;
    }

    cpptrace::stacktrace_frame frame;
    frame.filename = "test_package.cpp";
    frame.line = 20;
    frame.symbol = "main";
    const std::string rendered = frame.to_string();
    std::cout << "frame: " << rendered << std::endl;
    if (rendered.find("test_package.cpp") == std::string::npos) {
        std::cerr << "frame filename missing in rendering" << std::endl;
        return 1;
    }
    std::cout << "test_package: all checks passed" << std::endl;
    return 0;
}
