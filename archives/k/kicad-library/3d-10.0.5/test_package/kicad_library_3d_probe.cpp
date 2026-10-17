// Consumer probe for the installed KiCad 3D model resource tree.

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

void collect_dirs(const std::string& root, const std::string& suffix,
                  std::set<std::string>& result) {
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
        if (is_directory(path) && ends_with(name, suffix)) {
            result.insert(name);
        }
    }
    ::closedir(dir);
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

void collect_files_in(const std::string& dir, const std::string& suffix,
                      std::vector<std::string>& result) {
    DIR* handle = ::opendir(dir.c_str());
    if (!handle) {
        throw std::runtime_error("cannot open directory: " + dir);
    }
    while (dirent* entry = ::readdir(handle)) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") {
            continue;
        }
        const std::string path = join_path(dir, name);
        if (is_regular_file(path) && ends_with(name, suffix)) {
            result.push_back(path);
        }
    }
    ::closedir(handle);
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

bool valid_step(const std::string& text) {
    // KiCad STEP models follow ISO 10303-21; verify the mandatory
    // structural markers without parsing the full EXPRESS exchange file.
    if (text.size() < 24 ||
        text.compare(0, 13, "ISO-10303-21;") != 0) {
        return false;
    }
    return text.find("HEADER;") != std::string::npos &&
           text.find("FILE_SCHEMA") != std::string::npos &&
           text.find("ENDSEC;") != std::string::npos &&
           text.find("END-ISO-10303-21;") != std::string::npos;
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
            throw std::runtime_error("usage: kicad_library_3d_probe <resource-root> [--require-ohos]");
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
        const char* exported_root = std::getenv("KICAD10_3DMODEL_DIR");
        require(exported_root != nullptr,
                "KICAD10_3DMODEL_DIR is not exported by the Conan package", assertions);
        require(std::string(exported_root) == root,
                "KICAD10_3DMODEL_DIR does not match the tested resource root", assertions);

        std::set<std::string> shape_dirs;
        collect_dirs(root, ".3dshapes", shape_dirs);
        require(shape_dirs.size() == 105,
                "expected 105 .3dshapes directories, found " + std::to_string(shape_dirs.size()),
                assertions);

        for (const std::string& dir_name : shape_dirs) {
            std::vector<std::string> models;
            collect_files_in(join_path(root, dir_name), ".step", models);
            require(!models.empty(),
                    "empty .3dshapes directory: " + dir_name, assertions);
        }

        std::vector<std::string> steps;
        collect_files(root, ".step", steps);
        require(steps.size() == 7245,
                "expected 7245 .step files, found " + std::to_string(steps.size()), assertions);

        const std::vector<std::string> representative = {
            join_path(root, "Resistor_SMD.3dshapes/R_0805_2012Metric.step"),
            join_path(root, "Capacitor_SMD.3dshapes/CP_Elec_10x10.5.step"),
            join_path(root, "Battery.3dshapes/BatteryHolder_Keystone_1058_1x2032.step"),
            join_path(root, "LED_SMD.3dshapes/LED_0805_2012Metric.step"),
        };
        for (const std::string& path : representative) {
            require(is_regular_file(path), "missing representative model: " + path, assertions);
            require(valid_step(read_file(path)), "invalid representative STEP model: " + path,
                    assertions);
        }
        require(!valid_step("ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('TRUNCATED'));\n"),
                "truncated STEP input was accepted", assertions);

        std::cout << "kicad-library probe passed: assertions=" << assertions
                  << " shape_dirs=" << shape_dirs.size()
                  << " steps=" << steps.size()
                  << " ohos_build=" << (ohos_build ? "true" : "false") << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "kicad-library probe failed: " << error.what() << std::endl;
        return 1;
    }
}
