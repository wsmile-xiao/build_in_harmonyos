// test.cpp — libcutl L1 smoke test
// Verifies fs::path, exception, and compiler::type_id APIs are functional.

#include <libcutl/version.hxx>
#include <libcutl/exception.hxx>
#include <libcutl/fs/path.hxx>
#include <libcutl/compiler/type-id.hxx>

#include <iostream>
#include <sstream>

int main() {
    // 1. Version check
    if (LIBCUTL_VERSION != 100011000000000ULL) {
        std::cerr << "FAIL: version mismatch" << std::endl;
        return 1;
    }
    std::cout << "libcutl version: " << LIBCUTL_VERSION_STR << std::endl;

    // 2. fs::path API test
    cutl::fs::path p("test/path/file.txt");
    cutl::fs::path leaf = p.leaf();
    std::ostringstream oss;
    oss << leaf;
    if (oss.str() != "file.txt") {
        std::cerr << "FAIL: path leaf mismatch, got: " << oss.str() << std::endl;
        return 1;
    }
    std::cout << "Path leaf: " << oss.str() << std::endl;

    // 3. Exception API test
    try {
        throw cutl::exception();
    } catch (const cutl::exception& e) {
        if (e.what() == nullptr) {
            std::cerr << "FAIL: exception what() is null" << std::endl;
            return 1;
        }
        std::cout << "Exception caught: " << e.what() << std::endl;
    }

    // 4. compiler::type_id API test
    cutl::compiler::type_id tid(typeid(int));
    if (tid.name() == nullptr || tid.name()[0] == '\0') {
        std::cerr << "FAIL: type_id is null or empty" << std::endl;
        return 1;
    }
    std::cout << "type_id of int: " << tid.name() << std::endl;

    std::cout << "All tests passed!" << std::endl;
    return 0;
}
