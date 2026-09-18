#include "mmappable_vector.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

using mmap_allocator_namespace::READ_ONLY;
using mmap_allocator_namespace::READ_WRITE_SHARED;
using mmap_allocator_namespace::mmappable_vector;
using mmap_allocator_namespace::to_std_vector;

namespace {

std::string test_file() {
    const char* directory = std::getenv("TMPDIR");
    if (directory == nullptr || *directory == '\0') {
        directory = std::getenv("HOME");
    }
    if (directory == nullptr || *directory == '\0') {
        return "libmmap_allocator_conan_testfile";
    }
    return std::string(directory) + "/libmmap_allocator_conan_testfile";
}

void create_file(const std::string& path) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) {
        std::fprintf(stderr, "cannot create %s\n", path.c_str());
        std::exit(2);
    }
    for (int value = 0; value < 4; ++value) {
        output.write(reinterpret_cast<const char*>(&value), sizeof(value));
    }
}

}  // namespace

int main() {
    const std::string path = test_file();
    create_file(path);

    mmappable_vector<int> values;
    values.mmap_file(path, READ_ONLY, 0, 4);
    if (values.size() != 4 || values[0] != 0 || values[3] != 3) {
        return 3;
    }
    const std::vector<int> copied = to_std_vector(values);
    if (copied.size() != 4 || copied[1] != 1 || copied[2] != 2) {
        return 4;
    }

    values.munmap_file();
    mmappable_vector<int> shared;
    shared.mmap_file(path, READ_WRITE_SHARED, 0, 4);
    shared[2] = 42;
    shared.munmap_file();

    std::ifstream input(path, std::ios::binary);
    input.seekg(2 * static_cast<std::streamoff>(sizeof(int)));
    int persisted = 0;
    input.read(reinterpret_cast<char*>(&persisted), sizeof(persisted));
    std::remove(path.c_str());
    return persisted == 42 ? 0 : 5;
}
