// HarmonyOS 专项消费者测试 —— cmrc 2.0.1
// 目标：在 OHOS (aarch64, musl) 目标上实际编译运行，验证 cmrc 资源编译器
// 的完整 API 行为，而不只是复述上游 hello world 用例。
//
// 覆盖：
//   1. open() + 内容断言（嵌入文本资源）
//   2. exists()/is_file()/is_directory() 存在性 API
//   3. iterate_directory() 目录迭代（根 + 子目录两层）
//   4. open() 不存在资源必须抛 std::system_error（异常路径）
// 任一断言失败返回非零，CTest 即判定失败。
#include <cmrc/cmrc.hpp>

#include <iostream>
#include <string>
#include <system_error>

CMRC_DECLARE(ohos);

static int failures = 0;

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::cerr << "FAIL: " << msg << " @" << __LINE__ << '\n';     \
            ++failures;                                                   \
        }                                                                 \
    } while (0)

int main() {
    auto fs = cmrc::ohos::get_filesystem();

    // 1. open() + 内容断言
    auto data = fs.open("hello.txt");
    std::string content(data.begin(), data.end());
    std::cout << "open(hello.txt) -> " << content;
    CHECK(content == "Hello, world!\n", "embedded hello.txt content mismatch");

    // 2. 存在性 API
    CHECK(fs.exists("hello.txt"), "exists(hello.txt) should be true");
    CHECK(fs.is_file("hello.txt"), "is_file(hello.txt) should be true");
    CHECK(!fs.is_directory("hello.txt"), "is_directory(hello.txt) should be false");
    CHECK(fs.exists("subdir_a"), "exists(subdir_a) should be true");
    CHECK(fs.is_directory("subdir_a"), "is_directory(subdir_a) should be true");
    CHECK(!fs.exists("no-such-file.txt"), "exists(no-such-file) should be false");

    // 3. 目录迭代（根 + 子目录）
    int root_entries = 0;
    for (auto&& e : fs.iterate_directory("")) {
        std::cout << "root entry: " << e.filename() << '\n';
        ++root_entries;
    }
    CHECK(root_entries >= 2, "root directory should have >= 2 entries");

    int sub_entries = 0;
    for (auto&& e : fs.iterate_directory("subdir_a")) {
        std::cout << "subdir entry: " << e.filename() << '\n';
        ++sub_entries;
    }
    CHECK(sub_entries == 1, "subdir_a should have exactly 1 entry (subdir_b)");

    // 4. 异常路径：打开不存在资源必须抛 system_error
    bool threw = false;
    try {
        fs.open("no-such-file.txt");
    } catch (const std::system_error&) {
        threw = true;
    }
    CHECK(threw, "open(no-such-file) should throw std::system_error");

    if (failures == 0) {
        std::cout << "cmrc OHOS special test: ALL CHECKS PASSED\n";
        return 0;
    }
    std::cerr << "cmrc OHOS special test: " << failures << " check(s) FAILED\n";
    return 1;
}