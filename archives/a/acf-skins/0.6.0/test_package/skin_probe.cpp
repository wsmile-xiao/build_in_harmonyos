#include <dirent.h>
#include <sys/stat.h>

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Bytes = std::vector<unsigned char>;

class InvalidPngStructure final : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

Bytes read_file(const std::string& path) {
    std::ifstream input(path.c_str(), std::ios::binary | std::ios::ate);
    if (!input) {
        throw std::runtime_error("cannot read: " + path);
    }
    const std::streamoff end = input.tellg();
    if (end < 0) {
        throw std::runtime_error("cannot determine size: " + path);
    }
    input.seekg(0);
    Bytes bytes(static_cast<std::size_t>(end));
    if (!bytes.empty()) {
        input.read(reinterpret_cast<char*>(bytes.data()), end);
    }
    if (!input) {
        throw std::runtime_error("short read: " + path);
    }
    return bytes;
}

void validate_png(const std::string& path) {
    static const unsigned char signature[] = {
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
    };
    const Bytes bytes = read_file(path);
    if (bytes.size() < 33 || !std::equal(signature, signature + 8, bytes.begin()) ||
        std::string(reinterpret_cast<const char*>(bytes.data() + 12), 4) != "IHDR") {
        throw InvalidPngStructure("invalid PNG structure: " + path);
    }
}

void validate_jpeg(const std::string& path) {
    const Bytes bytes = read_file(path);
    if (bytes.size() < 4 || bytes[0] != 0xff || bytes[1] != 0xd8 ||
        bytes[bytes.size() - 2] != 0xff || bytes.back() != 0xd9) {
        throw std::runtime_error("invalid JPEG structure: " + path);
    }
}

void collect(const std::string& root, const std::string& relative,
             std::vector<std::string>& files) {
    const std::string directory = relative.empty() ? root : root + "/" + relative;
    using Dir = std::unique_ptr<DIR, int (*)(DIR*)>;
    Dir handle(opendir(directory.c_str()), closedir);
    if (!handle) {
        throw std::runtime_error("cannot open directory: " + directory);
    }
    while (dirent* entry = readdir(handle.get())) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") {
            continue;
        }
        const std::string child = relative.empty() ? name : relative + "/" + name;
        const std::string path = root + "/" + child;
        struct stat info {};
        if (stat(path.c_str(), &info) != 0) {
            throw std::runtime_error("cannot stat: " + path);
        }
        if (S_ISDIR(info.st_mode)) {
            collect(root, child, files);
        } else if (S_ISREG(info.st_mode)) {
            files.push_back(child);
        }
    }
}

std::string as_text(const std::string& path) {
    const Bytes bytes = read_file(path);
    if (bytes.empty()) {
        throw std::runtime_error("empty text resource: " + path);
    }
    return std::string(bytes.begin(), bytes.end());
}

void require_contains(const std::string& text, const std::string& token,
                      const std::string& path) {
    if (text.find(token) == std::string::npos) {
        throw std::runtime_error("missing token '" + token + "' in " + path);
    }
}

void validate_package(const std::string& root) {
    std::vector<std::string> files;
    collect(root, "", files);
    std::sort(files.begin(), files.end());
    if (files.size() != 81) {
        throw std::runtime_error("resource count mismatch: expected 81, got " +
                                 std::to_string(files.size()));
    }

    const std::set<std::string> inventory(files.begin(), files.end());
    const char* required[] = {
        "alps/alps.css",
        "clouds/clouds.js",
        "ice/ice.css",
        "snow/logo-135x135.png",
        "static/reset.css",
        "static/tango/16x16/status/network-wireless-encrypted.png",
        "wik/images/alogo.png",
        "wik/wik.js",
    };
    for (const char* file : required) {
        if (inventory.count(file) == 0) {
            throw std::runtime_error(std::string("missing packaged resource: ") + file);
        }
    }

    std::size_t css = 0;
    std::size_t javascript = 0;
    std::size_t png = 0;
    std::size_t jpeg = 0;
    for (const std::string& relative : files) {
        const std::string path = root + "/" + relative;
        if (ends_with(relative, ".css")) {
            ++css;
            as_text(path);
        } else if (ends_with(relative, ".js")) {
            ++javascript;
            as_text(path);
        } else if (ends_with(relative, ".png")) {
            ++png;
            validate_png(path);
        } else if (ends_with(relative, ".jpg")) {
            ++jpeg;
            validate_jpeg(path);
        } else {
            throw std::runtime_error("unexpected resource type: " + relative);
        }
    }
    if (css != 7 || javascript != 5 || png != 62 || jpeg != 7) {
        throw std::runtime_error("resource type counts do not match upstream inventory");
    }

    require_contains(as_text(root + "/ice/ice.css"), "url(\"alpine.jpg\")",
                     "ice/ice.css");
    require_contains(as_text(root + "/snow/snow.js"), "$(document).ready",
                     "snow/snow.js");
    std::cout << "PASS: parsed 81 packaged ACF skin resources" << std::endl;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--expect-invalid") {
            try {
                validate_png(argv[2]);
            } catch (const InvalidPngStructure&) {
                std::cout << "PASS: corrupted PNG rejected" << std::endl;
                return 0;
            }
            std::cerr << "FAIL: corrupted PNG was accepted" << std::endl;
            return 1;
        }
        if (argc != 2) {
            std::cerr << "usage: skin_probe <skins-root>" << std::endl;
            return 2;
        }
        validate_package(argv[1]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << std::endl;
        return 1;
    }
}
