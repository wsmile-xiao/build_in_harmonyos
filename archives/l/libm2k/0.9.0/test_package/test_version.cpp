#include <iostream>
#include <string>
#include <vector>
#include <libm2k/contextbuilder.hpp>

int main() {
    std::string ver = libm2k::context::ContextBuilder::getVersion();
    std::cout << "libm2k version: " << ver << std::endl;
    if (ver.empty()) {
        std::cerr << "FAIL: version is empty" << std::endl;
        return 1;
    }
    if (ver.find("0.9.0") == std::string::npos) {
        std::cerr << "WARN: version does not contain 0.9.0, got: " << ver << std::endl;
        // not fatal, allow any version but warn
    }
    std::vector<std::string> ctxs = libm2k::context::ContextBuilder::getAllContexts();
    std::cout << "getAllContexts size: " << ctxs.size() << std::endl;
    // Without hardware, may be 0, but call must not crash
    std::vector<libm2k::CONTEXT_INFO*> infos = libm2k::context::ContextBuilder::getContextsInfo();
    std::cout << "getContextsInfo size: " << infos.size() << std::endl;
    // clean up allocated CONTEXT_INFO
    for (auto *p : infos) {
        // free info? upstream allocates but test just leaks is okay; free if possible
        // CONTEXT_INFO fields are plain strings, no documented free function.
        // Avoid leak warnings: just delete if allocated with new (unknown).
        // Do not delete to avoid double-free; just ignore.
        (void)p;
    }
    std::cout << "PASS: version API works" << std::endl;
    return 0;
}
