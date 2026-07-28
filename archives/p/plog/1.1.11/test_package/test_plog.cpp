#include <plog/Appenders/IAppender.h>
#include <plog/Init.h>
#include <plog/Log.h>
#include <plog/Severity.h>

#include <cstring>
#include <iostream>
#include <string>

class CaptureAppender : public plog::IAppender
{
public:
    CaptureAppender()
        : count(0)
        , severity(plog::none)
    {
    }

    void write(const plog::Record& record) PLOG_OVERRIDE
    {
        ++count;
        severity = record.getSeverity();
        message = record.getMessage();
    }

    int count;
    plog::Severity severity;
    plog::util::nstring message;
};

int main(int argc, char** argv)
{
    if (argc == 2 && std::strcmp(argv[1], "--invalid-severity") == 0)
    {
        if (plog::severityFromString("not-a-severity") != plog::none)
        {
            std::cerr << "invalid severity was not rejected\n";
            return 1;
        }

        std::cout << "invalid severity rejected as NONE\n";
        return 0;
    }

    if (argc != 1)
    {
        std::cerr << "usage: test_plog [--invalid-severity]\n";
        return 2;
    }

    CaptureAppender appender;
    plog::Logger<PLOG_DEFAULT_INSTANCE_ID>& logger =
        plog::init(plog::info, &appender);

    PLOG_INFO << "OpenHarmony";
    PLOG_DEBUG << "filtered";

    if (appender.count != 1)
    {
        std::cerr << "severity filter did not suppress DEBUG\n";
        return 3;
    }
    if (appender.severity != plog::info)
    {
        std::cerr << "captured severity is not INFO\n";
        return 4;
    }
    if (appender.message != PLOG_NSTR("OpenHarmony"))
    {
        std::cerr << "captured INFO message differs\n";
        return 5;
    }
    if (logger.checkSeverity(plog::debug))
    {
        std::cerr << "DEBUG unexpectedly enabled\n";
        return 6;
    }

    logger.setMaxSeverity(plog::debug);
    PLOG_DEBUG << "debug-enabled";

    if (appender.count != 2)
    {
        std::cerr << "enabled DEBUG message was not captured\n";
        return 7;
    }
    if (appender.severity != plog::debug)
    {
        std::cerr << "captured severity is not DEBUG\n";
        return 8;
    }
    if (appender.message != PLOG_NSTR("debug-enabled"))
    {
        std::cerr << "captured DEBUG message differs\n";
        return 9;
    }
    if (std::strcmp(plog::severityToString(plog::warning), "WARN") != 0)
    {
        std::cerr << "severity string conversion differs\n";
        return 10;
    }

    std::cout << "plog consumer checks passed\n";
    return 0;
}
