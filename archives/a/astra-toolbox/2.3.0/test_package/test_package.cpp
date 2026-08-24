#include <iostream>
#include "astra/Globals.h"

int main() {
    int v = astra::getVersion();
    const char* vs = astra::getVersionString();
    std::cout << "astra-toolbox version=" << v << " (" << vs << ")" << std::endl;
    if (v != 203) {
        std::cerr << "unexpected version " << v << " expected 203 for 2.3.0" << std::endl;
        return 1;
    }
    std::cout << "smoke PASS" << std::endl;
    return 0;
}
