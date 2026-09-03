// nymphcast 0.2-alpha0 test_package - verify the packaged nymphcast_server
// executable is present, runnable and reports its version banner.
//
// The package is an application (no headers/libs exported), so the test
// genuinely invokes the packaged executable via the conanrun PATH and
// validates its version output. Upstream main() returns before any
// SDL/GUI init when --version is given (see NymphCastServer.cpp main()).
#include <cstdio>
#include <string>

int main() {
    // Real invocation of the packaged executable (resolved via conanrun PATH).
    FILE* pipe = popen("nymphcast_server --version 2>&1", "r");
    if (!pipe) {
        std::printf("FAIL: popen(nymphcast_server --version)\n");
        return 1;
    }
    char buf[256];
    std::string output;
    while (std::fgets(buf, (int)sizeof(buf), pipe)) {
        output += buf;
    }
    int status = pclose(pipe);
    if (status != 0) {
        std::printf("FAIL: nymphcast_server --version exit status %d\n", status);
        return 1;
    }
    if (output.find("NymphCast version:") == std::string::npos) {
        std::printf("FAIL: unexpected version output: %s\n", output.c_str());
        return 1;
    }
    std::printf("ok: %s", output.c_str());
    std::printf("nymphcast test_package: PASS\n");
    return 0;
}
