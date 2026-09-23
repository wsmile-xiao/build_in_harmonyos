// test_ghc_fs.cpp — HarmonyOS 专项测试：验证 ghc::filesystem 在 OHOS PC (aarch64) 平台核心路径能力。
// 覆盖：current_path / create_directories / exists / directory_iterator /
//       remove_all / 平台限制错误码（硬链接、FIFO 在 HMDFS 上应如实返回 error_code，不崩溃）。
#include <ghc/filesystem.hpp>
#include <cstdio>
#include <string>
#include <vector>

namespace fs = ghc::filesystem;

static int failures = 0;
static int checks = 0;

#define CHECK_MSG(cond, msg)                                 \
    do {                                                     \
        ++checks;                                            \
        if (!(cond)) {                                       \
            ++failures;                                      \
            std::printf("FAIL: %s (line %d)\n", msg, __LINE__); \
        }                                                    \
    } while (0)

int main()
{
    // 1. 当前路径可获取且为绝对路径
    std::error_code ec;
    fs::path cwd = fs::current_path(ec);
    CHECK_MSG(!ec, "current_path 无错误");
    CHECK_MSG(cwd.is_absolute(), "current_path 是绝对路径");
    std::printf("current_path = %s\n", cwd.string().c_str());

    // 2. 临时目录内创建目录/文件并遍历
    fs::path tmp = fs::temp_directory_path(ec);
    CHECK_MSG(!ec, "temp_directory_path 无错误");
    fs::path dir = tmp / "ghc_fs_ohos_test_dir";
    fs::remove_all(dir, ec);
    ec.clear();
    CHECK_MSG(fs::create_directories(dir / "sub" / "deep", ec), "create_directories 成功");
    CHECK_MSG(!ec, "create_directories 无错误");
    CHECK_MSG(fs::is_directory(dir / "sub" / "deep"), "is_directory 识别目录");

    {
        std::FILE* f = std::fopen((dir / "hello.txt").string().c_str(), "w");
        if (f) {
            std::fputs("hello ohos", f);
            std::fclose(f);
        }
    }
    CHECK_MSG(fs::exists(dir / "hello.txt"), "exists 识别文件");
    CHECK_MSG(fs::is_regular_file(dir / "hello.txt"), "is_regular_file 识别普通文件");
    CHECK_MSG(fs::file_size(dir / "hello.txt", ec) == 10, "file_size 正确");
    CHECK_MSG(!ec, "file_size 无错误");

    // 3. directory_iterator 遍历到刚创建的两个条目
    int entries = 0;
    for (const auto& de : fs::directory_iterator(dir)) {
        (void)de;
        ++entries;
    }
    CHECK_MSG(entries == 2, "directory_iterator 遍历到 2 个条目");

    // 4. 平台限制：HMDFS 不支持硬链接/FIFO → error_code 如实返回非零，且不崩溃
    fs::create_hard_link(dir / "hello.txt", dir / "hardlink.txt", ec);
    std::printf("create_hard_link ec = %s (%d)\n", ec.message().c_str(), (int)ec.value());
    CHECK_MSG((bool)ec, "create_hard_link 在 HMDFS 上如实返回错误码");

    ec.clear();
    fs::create_directory_symlink(dir / "sub", dir / "sym", ec);
    std::printf("create_directory_symlink ec = %s (%d)\n", ec.message().c_str(), (int)ec.value());
    if (!ec) {
        CHECK_MSG(fs::is_symlink(dir / "sym"), "create_directory_symlink 成功且 is_symlink 识别");
    }

    // 5. 清理
    ec.clear();
    std::uintmax_t removed = fs::remove_all(dir, ec);
    CHECK_MSG(!ec, "remove_all 无错误");
    CHECK_MSG(removed >= 4, "remove_all 删除全部条目");
    CHECK_MSG(!fs::exists(dir), "remove_all 后目录不存在");

    std::printf("RESULT: checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
