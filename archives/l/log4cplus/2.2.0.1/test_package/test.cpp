#include <log4cplus/log4cplus.h>
#include <log4cplus/configurator.h>
#include <log4cplus/logger.h>
#include <log4cplus/loggingmacros.h>

int main() {
    log4cplus::Initializer initializer;
    log4cplus::BasicConfigurator configurator;
    configurator.configure();
    const auto logger = log4cplus::Logger::getInstance(LOG4CPLUS_TEXT("consumer"));
    LOG4CPLUS_INFO(logger, LOG4CPLUS_TEXT("log4cplus consumer smoke"));
    return logger.isEnabledFor(log4cplus::INFO_LOG_LEVEL) ? 0 : 1;
}
