#include "mmappable_vector.h"

#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

#if !defined(MMAP_ALLOCATOR_HARMONYOS)
#error "The HarmonyOS consumer test must be built only for HarmonyOS."
#endif

using mmap_allocator_namespace::READ_WRITE_SHARED;
using mmap_allocator_namespace::mmappable_vector;

namespace {

std::string test_file() {
    const char* directory = std::getenv("TMPDIR");
    if (directory == nullptr || *directory == '\0') {
        directory = std::getenv("HOME");
    }
    if (directory == nullptr || *directory == '\0') {
        return "libmmap_allocator_ohos_testfile";
    }
    return std::string(directory) + "/libmmap_allocator_ohos_testfile";
}

}  // namespace

int main() {
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) {
        return 2;
    }
    if (ALIGN_TO_PAGE(page_size + 7) != page_size ||
        UPPER_ALIGN_TO_PAGE(page_size + 1) != 2 * page_size ||
        OFFSET_INTO_PAGE(page_size + 17) != 17) {
        return 3;
    }

    const std::string path = test_file();
    {
        std::ofstream output(path, std::ios::binary | std::ios::trunc);
        if (!output) {
            return 4;
        }
        for (int value = 10; value < 14; ++value) {
            output.write(reinterpret_cast<const char*>(&value), sizeof(value));
        }
    }

    mmappable_vector<int> values;
    values.mmap_file(path, READ_WRITE_SHARED, 0, 4);
    if (values[0] != 10 || values[3] != 13) {
        return 5;
    }
    values[1] = 99;
    values.munmap_file();

    std::ifstream input(path, std::ios::binary);
    input.seekg(static_cast<std::streamoff>(sizeof(int)));
    int persisted = 0;
    input.read(reinterpret_cast<char*>(&persisted), sizeof(persisted));
    std::remove(path.c_str());
    return persisted == 99 ? 0 : 6;
}
