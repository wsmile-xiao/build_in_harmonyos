#include <glob/glob.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static bool has_filename(const std::vector<fs::path>& paths, const std::string& name) {
    return std::any_of(paths.begin(), paths.end(), [&](const fs::path& path) {
        return path.filename() == name;
    });
}

int main() {
    const fs::path root = "glob_test_data";
    std::error_code error;
    fs::remove_all(root, error);
    fs::create_directories(root / "nested", error);
    if (error) {
        std::cerr << "create_directories failed: " << error.message() << "\n";
        return 1;
    }
    {
        std::ofstream(root / "one.txt") << "one\n";
        std::ofstream(root / "two.cpp") << "two\n";
        std::ofstream(root / "nested" / "deep.txt") << "deep\n";
    }

    const auto direct = glob::glob("glob_test_data/*.txt");
    if (direct.size() != 1 || !has_filename(direct, "one.txt")) {
        std::cerr << "direct glob mismatch\n";
        fs::remove_all(root, error);
        return 2;
    }

    const auto recursive = glob::rglob("glob_test_data/**");
    if (recursive.size() != 4 || !has_filename(recursive, "one.txt") ||
        !has_filename(recursive, "deep.txt")) {
        std::cerr << "recursive glob mismatch\n";
        fs::remove_all(root, error);
        return 3;
    }

    const auto multiple = glob::glob(std::vector<std::string>{
        "glob_test_data/*.txt", "glob_test_data/*.cpp"});
    if (multiple.size() != 2 || !has_filename(multiple, "one.txt") ||
        !has_filename(multiple, "two.cpp")) {
        std::cerr << "multiple-pattern glob mismatch\n";
        fs::remove_all(root, error);
        return 4;
    }

    fs::remove_all(root, error);
    if (error) {
        std::cerr << "cleanup failed: " << error.message() << "\n";
        return 5;
    }
    std::cout << "glob API checks passed\n";
    return 0;
}
