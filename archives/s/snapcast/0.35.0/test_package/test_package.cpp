// test_package source — verify snapcast binaries are callable
#include <cstdlib>
#include <iostream>

int main() {
    // The actual tests run snapserver --version and snapclient --version
    // from the test_package/conanfile.py test() method.
    // This C++ file exists to satisfy the test_package build requirement.
    std::cout << "snapcast test package built successfully" << std::endl;
    return 0;
}
