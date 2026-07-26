#include <mp4v2/mp4v2.h>

#include <filesystem>
#include <iostream>

int main()
{
    const auto path = std::filesystem::path("conan-test.mp4");
    std::error_code error;
    std::filesystem::remove(path, error);

    const auto file = MP4Create(path.string().c_str());
    if (file == MP4_INVALID_FILE_HANDLE) {
        std::filesystem::remove(path, error);
        return 1;
    }
    MP4Close(file);

    const auto is_regular_file = std::filesystem::is_regular_file(path, error);
    const auto size = is_regular_file ? std::filesystem::file_size(path, error) : 0;
    const auto created = is_regular_file && !error && size > 0;

    std::error_code cleanup_error;
    std::filesystem::remove(path, cleanup_error);
    if (!created || cleanup_error) {
        return 1;
    }

    std::cout << "mp4v2 file creation test passed" << std::endl;
    return 0;
}
