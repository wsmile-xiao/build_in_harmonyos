#include <boost/filesystem.hpp>

#include <fstream>
#include <iostream>

// NOTE: this test is built in Release (-DNDEBUG), so side effects such as
// create_directory() must NOT live inside assert() — they would be compiled
// away. Use explicit checks instead.

namespace fs = boost::filesystem;

int main() {
    const fs::path directory = "boost-filesystem-consumer";
    const fs::path file = directory / "payload.txt";
    fs::remove_all(directory);
    if (!fs::create_directory(directory)) {
        std::cerr << "boost filesystem test: failed to create " << directory << std::endl;
        return 1;
    }
    {
        std::ofstream out(file.string());
        if (!out) {
            std::cerr << "boost filesystem test: failed to open " << file << std::endl;
            return 1;
        }
        out << "OpenHarmony";
    }
    if (!fs::exists(file)) {
        std::cerr << "boost filesystem test: " << file << " does not exist" << std::endl;
        return 1;
    }
    if (fs::file_size(file) != 11) {
        std::cerr << "boost filesystem test: unexpected file size" << std::endl;
        return 1;
    }
    std::size_t entries = 0;
    for (fs::directory_iterator it(directory), end; it != end; ++it)
        ++entries;
    if (entries != 1) {
        std::cerr << "boost filesystem test: expected 1 entry, got " << entries << std::endl;
        return 1;
    }
    fs::remove_all(directory);
    std::cout << "boost filesystem consumer test passed" << std::endl;
    return 0;
}
