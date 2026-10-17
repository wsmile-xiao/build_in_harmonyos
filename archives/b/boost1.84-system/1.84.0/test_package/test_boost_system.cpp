// test_package/test_boost_system.cpp — boost1.84-system 1.84.0 L1 smoke test.
// Exercises the component-specific API surface: boost::system::error_code,
// error_condition, error_category, system_error, and std::error_code interop.
#include <boost/system/error_code.hpp>
#include <boost/system/system_error.hpp>
#include <boost/system/errc.hpp>
#include <iostream>
#include <string>
#include <system_error>

int main() {
    // 1. error_code construction + value/category access
    boost::system::error_code ec = boost::system::errc::make_error_code(
        boost::system::errc::no_such_file_or_directory);
    if (ec.value() != static_cast<int>(boost::system::errc::no_such_file_or_directory)) {
        std::cerr << "FAIL: error_code value mismatch" << std::endl;
        return 1;
    }
    if (std::string(ec.category().name()) != "generic") {
        std::cerr << "FAIL: generic category name mismatch: " << ec.category().name() << std::endl;
        return 1;
    }

    // 2. message() and comparison against errc enum
    std::string msg = ec.message();
    if (msg.empty()) {
        std::cerr << "FAIL: error_code message empty" << std::endl;
        return 1;
    }
    if (ec != boost::system::errc::no_such_file_or_directory) {
        std::cerr << "FAIL: errc comparison failed" << std::endl;
        return 1;
    }

    // 3. system_category errno mapping
    boost::system::error_code ec_sys(13, boost::system::system_category());
    if (ec_sys.value() != 13) {
        std::cerr << "FAIL: system category value" << std::endl;
        return 1;
    }

    // 4. default error_code == success
    boost::system::error_code ec_ok;
    if (ec_ok || ec_ok.value() != 0) {
        std::cerr << "FAIL: default error_code not success" << std::endl;
        return 1;
    }

    // 5. system_error throw/catch round-trip with context string
    try {
        throw boost::system::system_error(ec, "test_package context");
    } catch (const boost::system::system_error& e) {
        std::string what = e.what();
        if (what.find("test_package context") == std::string::npos) {
            std::cerr << "FAIL: system_error context lost: " << what << std::endl;
            return 1;
        }
        if (e.code() != ec) {
            std::cerr << "FAIL: system_error code mismatch" << std::endl;
            return 1;
        }
    }

    // 6. error_condition + interop with std::error_code (BOOST_SYSTEM_HAS_SYSTEM_ERROR)
    boost::system::error_condition en = ec.default_error_condition();
    if (en.value() != ec.value()) {
        std::cerr << "FAIL: default_error_condition mismatch" << std::endl;
        return 1;
    }
    std::error_code sec = ec;
    if (sec != std::make_error_code(std::errc::no_such_file_or_directory)) {
        std::cerr << "FAIL: std::error_code interop" << std::endl;
        return 1;
    }

    std::cout << "boost1.84-system smoke test OK: value=" << ec.value()
              << " msg=\"" << msg << "\" sys_cat=" << ec_sys.category().name() << std::endl;
    return 0;
}
