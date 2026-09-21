// Consumer probe for the installed KiCad footprint resource tree.

#include <dirent.h>
#include <sys/stat.h>

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

bool is_directory(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
}

bool is_regular_file(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

std::string join_path(const std::string& base, const std::string& name) {
    if (!base.empty() && (base.back() == '/' || base.back() == '\\')) {
        return base + name;
    }
    return base + "/" + name;
}

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

void collect_files(const std::string& root, const std::string& suffix,
                   std::vector<std::string>& result) {
    DIR* dir = ::opendir(root.c_str());
    if (!dir) {
        throw std::runtime_error("cannot open directory: " + root);
    }
    while (dirent* entry = ::readdir(dir)) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") {
            continue;
        }
        const std::string path = join_path(root, name);
        if (is_directory(path)) {
            collect_files(path, suffix, result);
        } else if (is_regular_file(path) && ends_with(name, suffix)) {
            result.push_back(path);
        }
    }
    ::closedir(dir);
}

void collect_pretty_dirs(const std::string& root, std::set<std::string>& result) {
    DIR* dir = ::opendir(root.c_str());
    if (!dir) {
        throw std::runtime_error("cannot open directory: " + root);
    }
    while (dirent* entry = ::readdir(dir)) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") {
            continue;
        }
        const std::string path = join_path(root, name);
        if (is_directory(path) && ends_with(name, ".pretty")) {
            result.insert(name);
        }
    }
    ::closedir(dir);
}

std::string read_file(const std::string& path) {
    std::ifstream input(path.c_str(), std::ios::in | std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot read file: " + path);
    }
    std::ostringstream content;
    content << input.rdbuf();
    return content.str();
}

bool balanced_sexp(const std::string& text) {
    int depth = 0;
    bool quoted = false;
    bool escaped = false;
    bool comment = false;
    bool saw_root = false;
    for (char raw : text) {
        const unsigned char c = static_cast<unsigned char>(raw);
        if (comment) {
            if (raw == '\n') {
                comment = false;
            }
            continue;
        }
        if (escaped) {
            escaped = false;
            continue;
        }
        if (quoted && raw == '\\') {
            escaped = true;
            continue;
        }
        if (!quoted && raw == ';') {
            comment = true;
            continue;
        }
        if (raw == '"') {
            quoted = !quoted;
            continue;
        }
        if (quoted) {
            continue;
        }
        if (raw == '(') {
            ++depth;
            saw_root = true;
        } else if (raw == ')') {
            if (--depth < 0) {
                return false;
            }
        }
    }
    return saw_root && !quoted && !escaped && depth == 0;
}

bool valid_footprint(const std::string& text) {
    return !text.empty() && balanced_sexp(text) &&
           text.find("(footprint ") != std::string::npos &&
           text.find("(version ") != std::string::npos &&
           text.find("(generator ") != std::string::npos &&
           text.find("(property \"Reference\" ") != std::string::npos &&
           text.find("(property \"Value\" ") != std::string::npos &&
           text.find("(pad ") != std::string::npos;
}

void require(bool condition, const std::string& message, int& assertions) {
    ++assertions;
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            throw std::runtime_error("usage: kicad_footprints_probe <resource-root> [--require-ohos]");
        }
        const std::string root = argv[1];
        bool require_ohos = false;
        for (int i = 2; i < argc; ++i) {
            if (std::string(argv[i]) == "--require-ohos") {
                require_ohos = true;
            }
        }
#ifdef __OHOS__
        const bool ohos_build = true;
#else
        const bool ohos_build = false;
#endif
        int assertions = 0;
        require(is_directory(root), "resource root is not a directory: " + root, assertions);
        require(!require_ohos || ohos_build,
                "--require-ohos requested but probe was not compiled with __OHOS__", assertions);
        const char* exported_root = std::getenv("KICAD10_FOOTPRINT_DIR");
        require(exported_root != nullptr,
                "KICAD10_FOOTPRINT_DIR is not exported by the Conan package", assertions);
        require(std::string(exported_root) == root,
                "KICAD10_FOOTPRINT_DIR does not match the tested resource root", assertions);

        const std::string table = join_path(join_path(root, "../template"), "fp-lib-table");
        require(is_regular_file(table), "fp-lib-table is missing: " + table, assertions);
        const std::string table_text = read_file(table);
        require(table_text.find("${KICAD10_FOOTPRINT_DIR}") != std::string::npos,
                "fp-lib-table does not use KICAD10_FOOTPRINT_DIR", assertions);

        std::set<std::string> pretty_dirs;
        collect_pretty_dirs(root, pretty_dirs);
        require(pretty_dirs.size() == 155,
                "expected 155 .pretty directories, found " + std::to_string(pretty_dirs.size()), assertions);

        size_t table_libraries = 0;
        size_t cursor = 0;
        for (;;) {
            const size_t marker = table_text.find("(lib (name \"", cursor);
            if (marker == std::string::npos) {
                break;
            }
            ++table_libraries;
            const size_t name_end = table_text.find(".pretty\"", marker);
            require(name_end != std::string::npos, "fp-lib-table entry lacks .pretty URI", assertions);
            const size_t slash = table_text.rfind('/', name_end - 1);
            require(slash != std::string::npos, "fp-lib-table entry URI is malformed", assertions);
            const std::string dir_name = table_text.substr(slash + 1, name_end + 7 - slash - 1);
            require(pretty_dirs.count(dir_name) == 1,
                    "fp-lib-table references missing directory: " + dir_name, assertions);
            cursor = name_end + 7;
        }
        require(table_libraries == 155,
                "expected 155 fp-lib-table entries, found " + std::to_string(table_libraries), assertions);

        std::vector<std::string> modules;
        collect_files(root, ".kicad_mod", modules);
        require(modules.size() == 15435,
                "expected 15435 .kicad_mod files, found " + std::to_string(modules.size()), assertions);

        const std::vector<std::string> representative = {
            join_path(root, "Package_DIP.pretty/DIP-8_W7.62mm.kicad_mod"),
            join_path(root, "Connector_Molex.pretty/Molex_Micro-Fit_3.0_43650-0200_1x02_P3.00mm_Horizontal.kicad_mod"),
            join_path(root, "Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod"),
        };
        for (const std::string& path : representative) {
            require(valid_footprint(read_file(path)), "invalid representative footprint: " + path, assertions);
        }
        require(!valid_footprint("(footprint \"broken\" (property \"Value\" \"x\")"),
                "malformed footprint was accepted", assertions);
        std::cout << "kicad-footprints probe passed: assertions=" << assertions
                  << " pretty_dirs=" << pretty_dirs.size()
                  << " modules=" << modules.size()
                  << " ohos_build=" << (ohos_build ? "true" : "false") << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "kicad-footprints probe failed: " << error.what() << std::endl;
        return 1;
    }
}
