// HarmonyOS-specific consumer test for kicad-library-templates/10.0.5.

#if !defined(__OHOS__)
#error "kicad_templates_harmonyos_probe must be compiled for HarmonyOS"
#endif
#if !defined(__aarch64__) && !defined(__x86_64__)
#error "kicad_templates_harmonyos_probe must target HarmonyOS aarch64 or x86_64"
#endif

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string read_with_posix(const std::string& path) {
    const int fd = ::open(path.c_str(), O_RDONLY);
    require(fd >= 0, "open failed for: " + path + ", errno=" + std::to_string(errno));

    char buffer[128] = {};
    const ssize_t count = ::read(fd, buffer, sizeof(buffer));
    const int close_result = ::close(fd);
    require(close_result == 0, "close failed for: " + path);
    require(count > 0, "read returned no data for: " + path);
    return std::string(buffer, static_cast<size_t>(count));
}

void check_prefix(const std::string& path, const std::string& expected) {
    const std::string data = read_with_posix(path);
    const size_t first = data.find_first_not_of(" \t\r\n");
    require(first != std::string::npos && data.compare(first, expected.size(), expected) == 0,
            "unexpected file signature for: " + path);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: kicad_templates_harmonyos_probe <template-resource-root>\n";
        return 2;
    }

    try {
        const std::string root(argv[1]);
        struct stat resource_stat {};
        require(::stat(root.c_str(), &resource_stat) == 0 && S_ISDIR(resource_stat.st_mode),
                "HarmonyOS resource root is not a directory: " + root);

        const std::string project = root + "/Projects/API_Series-500/API_Series-500.kicad_pro";
        const std::string worksheet = root + "/A2_ISO5457-1999_ISO7200-2004_EN.kicad_wks";
        check_prefix(project, "{");
        check_prefix(worksheet, "(page_layout");

        std::cout << "HarmonyOS-specific probe passed: __OHOS__ and a supported PC architecture "
                  << "defined, "
                  << "POSIX resource reads succeeded\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "HarmonyOS-specific probe FAILED: " << error.what() << "\n";
        return 1;
    }
}
