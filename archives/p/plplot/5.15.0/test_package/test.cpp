#include <cstring>
#include <iostream>
#include <plplot.h>
#include <plstream.h>

int main() {
    char c_version[80] = {};
    plgver(c_version);
    if (std::strncmp(c_version, "5.15", 4) != 0) {
        std::cerr << "unexpected C API version: " << c_version << std::endl;
        return 1;
    }

    plstream stream;
    char cxx_version[80] = {};
    stream.gver(cxx_version);
    if (std::strcmp(c_version, cxx_version) != 0) {
        std::cerr << "C/C++ version mismatch: " << c_version
                  << " vs " << cxx_version << std::endl;
        return 2;
    }

    if (sizeof(PLFLT) == 0 || sizeof(PLINT) == 0) {
        std::cerr << "invalid PLplot public ABI types" << std::endl;
        return 3;
    }

    std::cout << "plplot functional checks passed: 4" << std::endl;
    return 0;
}
