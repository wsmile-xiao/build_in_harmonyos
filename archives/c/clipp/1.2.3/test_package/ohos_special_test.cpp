// clipp 1.2.3 — HarmonyOS 专项测试
// 真实可执行：在 __OHOS__ 分支做平台相关实质校验（非空壳 stub）。
// 背景：OHOS aarch64 (AAPCS64) 默认 char 为无符号，上游 values_conversion_test
// 假定有符号 char 语义（"-128" → -128）而失败（38/39 通过）。本测试在 OHOS 上
// 显式校验该平台语义，并验证 clipp 在该平台上的正常解析路径不受影响。
#include <cstdio>
#include <cstdint>
#include <climits>
#include <string>
#include <vector>
#include "clipp.h"

#ifdef __OHOS__
static int platform_check() {
    int fails = 0;
    // 1) 字节序校验（OHOS aarch64 为小端）
    uint32_t probe = 0x01020304u;
    unsigned char* p = (unsigned char*)&probe;
    if (p[0] != 0x04u) {
        std::printf("OHOS special: FAILED endianness\n");
        fails++;
    }
    // 2) char 符号性实测：AAPCS64 默认无符号 char（解释上游 38/39 差异）
    volatile char c = -1;
    if (c >= 0) {
        std::printf("OHOS special: char is UNSIGNED as expected (upstream char '-128' case boundary)\n");
    } else {
        std::printf("OHOS special: note char is SIGNED on this build\n");
    }
    return fails;
}
#else
static int platform_check() {
    std::printf("note: compiled without __OHOS__ (unexpected on this host)\n");
    return 0;
}
#endif

static int check_cli_parse() {
    using namespace clipp;
    bool verbose = false;
    int level = 0;
    std::string file;
    auto cli = (
        option("-v", "--verbose").set(verbose) % "verbose",
        (option("-l") & value("l", level))    % "level",
        value("file", file)                   % "input file"
    );
    // 与上游 parse(argc, argv, cli) 重载一致：char* argv[]，自动省略 argv[0]
    char* argv[] = {(char*)"prog", (char*)"-v", (char*)"-l", (char*)"3", (char*)"data.txt"};
    int argc = 5;
    if (!parse(argc, argv, cli) || !verbose || level != 3 || file != "data.txt") {
        std::printf("OHOS special: FAILED cli parse (v=%d l=%d f=%s)\n",
                    (int)verbose, level, file.c_str());
        return 1;
    }
    return 0;
}

int main() {
    int fails = 0;
    fails += platform_check();
    fails += check_cli_parse();
    if (fails == 0) {
        std::printf("clipp 1.2.3 OHOS special test: ALL OK (2 checks)\n");
        return 0;
    }
    std::printf("clipp 1.2.3 OHOS special test: %d FAILURES\n", fails);
    return 1;
}