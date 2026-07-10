// Minimal test: verify pyCXX package structure and version (R34)
#include "CXX/Version.hxx"
#include <iostream>
#include <cassert>

int main()
{
    // Verify pyCXX version macros are accessible
    std::cout << "PyCXX version: " << PYCXX_VERSION_MAJOR << "."
              << PYCXX_VERSION_MINOR << "." << PYCXX_VERSION_PATCH << std::endl;

    // Verify expected version 6.2.3
    assert(PYCXX_VERSION_MAJOR == 6);
    assert(PYCXX_VERSION_MINOR == 2);
    assert(PYCXX_VERSION_PATCH == 3);
    assert(PYCXX_VERSION == ((6<<16)|(2<<8)|(3)));

    std::cout << "All assertions passed!" << std::endl;
    return 0;
}
