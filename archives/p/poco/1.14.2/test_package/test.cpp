#include <Poco/DateTime.h>
#include <Poco/DateTimeFormat.h>
#include <Poco/DateTimeFormatter.h>
#include <Poco/Version.h>
#include <iostream>

int main() {
    // Test Poco::DateTime (Foundation module)
    Poco::DateTime dt(2026, 1, 1);
    std::string formatted = Poco::DateTimeFormatter::format(dt, Poco::DateTimeFormat::ISO8601_FORMAT);
    std::cout << "Poco version: " << POCO_VERSION << std::endl;
    std::cout << "DateTime: " << formatted << std::endl;

    // Verify the date was constructed correctly (explicit checks, not assert, for Release mode)
    if (dt.year() != 2026) { std::cerr << "FAIL: year mismatch" << std::endl; return 1; }
    if (dt.month() != 1) { std::cerr << "FAIL: month mismatch" << std::endl; return 1; }
    if (dt.day() != 1) { std::cerr << "FAIL: day mismatch" << std::endl; return 1; }

    std::cout << "test poco 1.14.2: OK" << std::endl;
    return 0;
}
