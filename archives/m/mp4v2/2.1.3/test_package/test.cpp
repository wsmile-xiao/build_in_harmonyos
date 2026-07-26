#include <mp4v2/mp4v2.h>

#include <filesystem>
#include <iostream>

int main()
{
    const auto path = std::filesystem::path("conan-test.mp4");
    const auto file = MP4Create(path.string().c_str());
    if (file == MP4_INVALID_FILE_HANDLE) {
        return 1;
    }
    MP4Close(file);

    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0) {
        return 1;
    }

    std::cout << "mp4v2 file creation test passed" << std::endl;
    return 0;
}
