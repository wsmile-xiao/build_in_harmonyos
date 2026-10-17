// test_glog.cpp — Verifies glog library is functional
// Uses glog API: google::InitGoogleLogging, LOG(INFO), CHECK

#include <glog/logging.h>
#include <cstdlib>
#include <string>

int main(int argc, char* argv[]) {
    // Initialize glog
    google::InitGoogleLogging(argv[0]);

    // Log a message at INFO level
    LOG(INFO) << "glog test: basic logging works";

    // Log at different severity levels
    LOG(WARNING) << "glog test: warning level works";
    LOG(ERROR) << "glog test: error level works";

    // Use CHECK macro
    CHECK_EQ(1 + 1, 2) << "glog test: CHECK_EQ works";

    // Use VLOG if verbose logging is compiled
    VLOG(1) << "glog test: verbose logging works";

    // Shutdown glog
    google::ShutdownGoogleLogging();

    return 0;
}
