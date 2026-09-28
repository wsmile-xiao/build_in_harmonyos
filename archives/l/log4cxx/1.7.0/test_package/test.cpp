#include <log4cxx/logger.h>
#include <log4cxx/basicconfigurator.h>
#include <log4cxx/consoleappender.h>
#include <log4cxx/level.h>
#include <cassert>
#include <iostream>

using namespace log4cxx;

int main() {
    // Real consumer usage: configure the framework and use a named logger.
    BasicConfigurator::configure();
    LoggerPtr logger = Logger::getLogger(LOG4CXX_STR("org.apache.log4cxx.consumer"));
    assert(logger != nullptr);
    logger->setLevel(Level::getInfo());

    // Exercise the logging API — must compile against and link the real library.
    LOG4CXX_INFO(logger, "log4cxx consumer test message");
    LOG4CXX_WARN(logger, "log4cxx consumer warning message");

    // Verify the logger is usable after writing (framework state remains valid).
    assert(logger->isInfoEnabled());

    std::cout << "log4cxx consumer test: PASS" << std::endl;
    return 0;
}
