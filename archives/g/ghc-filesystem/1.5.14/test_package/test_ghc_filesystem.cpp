#include <ghc/filesystem.hpp>
#include <cstdio>
#include <string>

namespace fs = ghc::filesystem;

// R34: test_package 必须实质调用被测包 API —— 真实操作 ghc::filesystem 并断言结果。
int main() {
    int failures = 0;

    // 1) path 构造与拼接
    const fs::path base = fs::temp_directory_path() / "ghc-filesystem-test-pkg";
    fs::remove_all(base);
    if (fs::exists(base)) {
        std::fprintf(stderr, "FAIL: remove_all 后路径仍存在\n");
        ++failures;
    }

    // 2) create_directories + is_directory
    const fs::path sub = base / "a" / "b" / "c";
    if (!fs::create_directories(sub)) {
        std::fprintf(stderr, "FAIL: create_directories 返回 false\n");
        ++failures;
    }
    if (!fs::exists(sub) || !fs::is_directory(sub)) {
        std::fprintf(stderr, "FAIL: 目录不存在或不是目录\n");
        ++failures;
    }

    // 3) 遍历 + 文件写入
    std::FILE* f = std::fopen((base / "hello.txt").c_str(), "w");
    if (f != nullptr) {
        std::fputs("hello", f);
        std::fclose(f);
    }
    int count = 0;
    for (const auto& entry : fs::directory_iterator(base)) {
        (void)entry;
        ++count;
    }
    if (count != 2) {
        std::fprintf(stderr, "FAIL: directory_iterator 计数=%d 期望=2\n", count);
        ++failures;
    }

    // 4) 相对/绝对路径判断
    if (!fs::path("/x").is_absolute() || fs::path("x").is_absolute()) {
        std::fprintf(stderr, "FAIL: is_absolute 判断错误\n");
        ++failures;
    }

    fs::remove_all(base);

    if (failures != 0) {
        std::fprintf(stderr, "FAIL: %d 项检查失败\n", failures);
        return 1;
    }
    std::printf("PASS: ghc::filesystem header-only API OK\n");
    return 0;
}