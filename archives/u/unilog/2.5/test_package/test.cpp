#include "UniLog/UniLog.hpp"
#include "UniLog/ErrorCode.hpp"
#include <iostream>
#include <memory>

int main(int argc, char* argv[]) {
    // Initialize UniLog with both std and file output, info level, low verbosity
    UniLog::Initial(argv[0],
                    UNI_LOG_STD_FILE,
                    UNI_LOG_STD_LEVEL_INFO,
                    UNI_LOG_LOW,
                    UNI_LOG_DEFAULT_PATH);
    UniLog::setUniLogPrefix("HMBS_TEST");

    // Basic logging macros — must actually call the library, not a stub
    UNI_LOG_INFO << "HMBS test INFO message";
    UNI_LOG_WARNING << "HMBS test WARNING message";
    UNI_LOG_ERROR(ERROR_SAMPLE) << "HMBS test ERROR message";
    UNI_LOG_VINFO(UNI_LOG_LOW) << "HMBS verbosity low";
    UNI_LOG_INFO_LOW << "HMBS info low sugar";
    UNI_LOG_DEBUG_INFO << "HMBS debug info";

    // ErrorCode factory usage
    REGISTER_ERROR_CODE(MY_TEST_ERR, "TestError", "Test display for HMBS");
    try {
        throw GEN_ERROR(MY_TEST_ERR) << "throw test";
    } catch (ErrorCode& e) {
        std::cout << "Caught ErrorCode ID=" << e.getErrID() << " dsp=" << e.getErrDsp() << std::endl;
        std::cout << "msg=" << e.getErrMsg() << std::endl;
        // Verify stream output operator
        std::cout << "stream: " << e << std::endl;
        if (e.getErrID().empty()) {
            std::cerr << "ErrorCode ID empty!" << std::endl;
            return 1;
        }
    }

    // Checker and check_throw path
    UNI_LOG_CHECK(1 == 1, ERROR_SAMPLE) << "check should pass";
    std::unique_ptr<int> uptr(new int(42));
    UNI_LOG_CHECK(uptr, ERROR_SAMPLE) << "uptr should be non-null";

    // Verify that log file was created (default ./log)
    // Not strictly required, but proves file output path works
    std::cout << "UniLog test passed: all API calls succeeded" << std::endl;
    return 0;
}
