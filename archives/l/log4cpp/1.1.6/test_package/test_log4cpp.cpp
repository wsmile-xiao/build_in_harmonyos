#include <log4cpp/Category.hh>
#include <log4cpp/NDC.hh>
#include <log4cpp/OstreamAppender.hh>
#include <log4cpp/PatternLayout.hh>
#include <log4cpp/Priority.hh>

#include <algorithm>
#include <iostream>
#include <sstream>
#include <string>

int main()
{
    constexpr int expected_checks = 17;
    int checks = 0;
    bool failed = false;

#define CHECK(condition, message)                                             \
    do {                                                                      \
        ++checks;                                                             \
        if (!(condition)) {                                                   \
            std::cerr << "check " << checks << " failed: " << message        \
                      << std::endl;                                           \
            failed = true;                                                    \
        }                                                                     \
    } while (0)

    std::ostringstream output;
    log4cpp::Category &root = log4cpp::Category::getRoot();
    root.removeAllAppenders();
    root.setPriority(log4cpp::Priority::DEBUG);

    log4cpp::OstreamAppender *appender =
        new log4cpp::OstreamAppender("memory", &output);
    log4cpp::PatternLayout *layout = new log4cpp::PatternLayout();
    layout->setConversionPattern("%p|%c|%m%n");
    appender->setLayout(layout);
    root.addAppender(appender);

    log4cpp::Category &category =
        log4cpp::Category::getInstance("consumer");

    CHECK(
        root.getPriority() == log4cpp::Priority::DEBUG,
        "root priority is DEBUG"
    );
    CHECK(category.getName() == "consumer", "category name matches");
    CHECK(
        root.getAppender("memory") == appender,
        "named appender is registered"
    );
    CHECK(
        log4cpp::Priority::getPriorityName(log4cpp::Priority::DEBUG)
            == "DEBUG",
        "priority name lookup succeeds"
    );
    CHECK(
        log4cpp::Priority::getPriorityValue("ERROR")
            == log4cpp::Priority::ERROR,
        "priority value lookup succeeds"
    );

    log4cpp::NDC::clear();
    CHECK(log4cpp::NDC::getDepth() == 0, "NDC begins empty");
    log4cpp::NDC::push("request-42");
    CHECK(log4cpp::NDC::getDepth() == 1, "NDC push changes depth");
    CHECK(log4cpp::NDC::get() == "request-42", "NDC value matches");
    CHECK(log4cpp::NDC::pop() == "request-42", "NDC pop returns value");
    CHECK(log4cpp::NDC::getDepth() == 0, "NDC is empty after pop");

    category.debug("debug-message");
    category.info("info-message");
    category.warn("warn-message");
    category.error("error-message");

    const std::string text = output.str();
    CHECK(
        text.find("DEBUG|consumer|debug-message") != std::string::npos,
        "DEBUG message is formatted"
    );
    CHECK(
        text.find("INFO|consumer|info-message") != std::string::npos,
        "INFO message is formatted"
    );
    CHECK(
        text.find("WARN|consumer|warn-message") != std::string::npos,
        "WARN message is formatted"
    );
    CHECK(
        text.find("ERROR|consumer|error-message") != std::string::npos,
        "ERROR message is formatted"
    );
    CHECK(
        text.find("|consumer|") != std::string::npos,
        "category is present in formatted output"
    );
    CHECK(
        std::count(text.begin(), text.end(), '\n') == 4,
        "exactly four log records are emitted"
    );
    CHECK(
        text.find("FATAL|") == std::string::npos,
        "no unrequested FATAL record is emitted"
    );

    log4cpp::Category::shutdownForced();

    if (checks != expected_checks) {
        std::cerr << "expected " << expected_checks << " checks, executed "
                  << checks << std::endl;
        return 3;
    }

    if (failed) {
        return 2;
    }

    std::cout << "log4cpp consumer tests: " << checks
              << "/" << expected_checks << " passed" << std::endl;
    return 0;
}
