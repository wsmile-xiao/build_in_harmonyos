#include <log4cpp/BasicLayout.hh>
#include <log4cpp/Category.hh>
#include <log4cpp/NDC.hh>
#include <log4cpp/OstreamAppender.hh>
#include <log4cpp/Priority.hh>

#include <exception>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

struct TestContext {
    TestContext()
        : root(log4cpp::Category::getRoot()) {
        auto* appender = new log4cpp::OstreamAppender("stream", &output);
        appender->setLayout(new log4cpp::BasicLayout());
        root.setPriority(log4cpp::Priority::WARN);
        root.addAppender(appender);
    }

    std::ostringstream output;
    log4cpp::Category& root;
};

void test_priority_filter(TestContext& context) {
    context.root.info("hidden informational message");
    context.root.warn("visible warning message");

    const std::string log = context.output.str();
    require(log.find("visible warning message") != std::string::npos, "warn message missing");
    require(log.find("hidden informational message") == std::string::npos, "priority filter did not hide info");
}

void test_ostream_appender(TestContext& context) {
    context.root.error("layout output message");
    require(context.output.str().find("layout output message") != std::string::npos, "OstreamAppender output missing");
}

void test_ndc(TestContext&) {
    log4cpp::NDC::push("request-42");
    require(log4cpp::NDC::get() == "request-42", "NDC push/get failed");
    require(log4cpp::NDC::pop() == "request-42", "NDC pop failed");
    require(log4cpp::NDC::get().empty(), "NDC stack was not cleared");
}

void test_stream_api(TestContext& context) {
    context.root << log4cpp::Priority::ERROR << "streamed error message";
    require(context.output.str().find("streamed error message") != std::string::npos, "Category stream API failed");
}

void run_case(const char* name, void (*test)(TestContext&), TestContext& context, unsigned int& passed) {
    try {
        test(context);
    } catch (const std::exception& error) {
        throw std::runtime_error(std::string(name) + ": " + error.what());
    }

    ++passed;
    std::cout << "PASS: " << name << std::endl;
}

}  // namespace

int main() {
    const unsigned int total = 4;
    unsigned int passed = 0;
    TestContext context;

    try {
        run_case("Category priority filtering", test_priority_filter, context, passed);
        run_case("OstreamAppender with BasicLayout", test_ostream_appender, context, passed);
        run_case("NDC push/pop", test_ndc, context, passed);
        run_case("Category stream API", test_stream_api, context, passed);
    } catch (const std::exception& error) {
        log4cpp::Category::shutdown();
        std::cerr << "FAIL: " << error.what() << std::endl;
        return 1;
    }

    log4cpp::Category::shutdown();
    std::cout << "Consumer smoke summary: " << passed << "/" << total << " passed" << std::endl;
    return passed == total ? 0 : 1;
}
