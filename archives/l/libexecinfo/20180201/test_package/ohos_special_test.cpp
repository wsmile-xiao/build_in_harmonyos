// libexecinfo 20180201 — HarmonyOS 专项测试
//
// 真实可执行：在 __OHOS__ 分支做平台相关实质校验（非空壳 stub）。
// 背景：OHOS aarch64 运行时为 musl 系 libc，glibc 的 <execinfo.h>/backtrace()
// 在 musl 上默认不可用（knowledge/musl-glibc-*-comparison 均有记录）；
// libexecinfo 正是为此类平台提供 backtrace 设施。本测试在 OHOS 上显式校验：
//   1) 平台宏与架构（aarch64 / __OHOS__）
//   2) backtrace() 能捕获真实调用栈帧（递归制造 ≥3 层深度）
//   3) backtrace_symbols_fd() 能把帧映射回模块路径（OHOS 动态加载器可解析）
// 非 OHOS 平台同样执行相同的 backtrace 调用路径，保证任一平台构建都能真正
// 运行而非空壳（与 boost-te/clipp 专项测试同构）。
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <unistd.h>
#include <execinfo.h>

#if defined(__OHOS__)
static constexpr bool kOnOhos = true;
static_assert(__OHOS__ == 1, "__OHOS__ must be defined as 1 on OHOS");
#else
static constexpr bool kOnOhos = false;
#endif

#define MAX_FRAMES 64

static int depth_check(int remaining)
{
    void *frames[MAX_FRAMES];
    int n;
    int fails = 0;

    /* 返回值必须透传：内层 depth_check() 的 fails 累加必须传回 main，
     * 否则 __aarch64__ 缺失或 backtrace() 帧数不足时仍会误报 PASS。 */
    if (remaining > 0) {
        return depth_check(remaining - 1);
    }

    // 1) 平台/架构自检
#if defined(__aarch64__)
    std::printf("OHOS special: __aarch64__ defined (expected on armv8)\n");
#else
    std::printf("OHOS special: WARNING __aarch64__ not defined\n");
    fails++;
#endif
    if (kOnOhos)
        std::printf("OHOS special: running on OHOS (%s)\n", "aarch64-linux-ohos");

    // 2) backtrace() 真实捕获帧
    n = backtrace(frames, MAX_FRAMES);
    std::printf("OHOS special: backtrace() returned %d frames\n", n);
    if (n <= 0) {
        // P3 修复：拦截负值/零值。负 int 转 size_t 会变成巨大帧数传给
        // backtrace_symbols_fd，导致越界读取；与同 PR 的 test.c 行为一致，
        // 负值/零值直接判失败并返回，不再继续符号解析。
        std::printf("OHOS special: FAILED backtrace() returned %d frames\n", n);
        fails++;
        return fails;
    }
    if (n < 3) {
        std::printf("OHOS special: FAILED expected >=3 frames, got %d\n", n);
        fails++;
    }

    // 3) 帧映射回模块（backtrace_symbols 走 dladdr 解析，不依赖 glibc）
    // P3 修复：真实断言——每个符号串必须非 NULL 且非空，行数必须等于帧数；
    // 仅调用 backtrace_symbols_fd 不做校验不构成门禁。
    {
        char **syms = backtrace_symbols(frames, n);
        int sym_fails = 0;
        if (syms == nullptr) {
            std::printf("OHOS special: FAILED backtrace_symbols() returned NULL\n");
            fails++;
        } else {
            for (int i = 0; i < n; i++) {
                if (syms[i] == nullptr || syms[i][0] == '\0') {
                    std::printf("OHOS special: FAILED symbol[%d] empty\n", i);
                    sym_fails++;
                }
            }
            if (sym_fails == 0) {
                std::printf("OHOS special: symbol resolution verified %d non-empty lines\n", n);
            } else {
                fails += sym_fails;
            }
            std::free(syms);
        }
    }
    // 保留符号输出以便人工核对（断言已在上面完成）
    backtrace_symbols_fd(frames, n, STDOUT_FILENO);
    return fails;
}

int main()
{
    int rc = depth_check(4);
    if (rc == 0)
        std::printf("PASS: libexecinfo HarmonyOS special test passed\n");
    else
        std::printf("FAIL: libexecinfo HarmonyOS special test failed (%d)\n", rc);
    return rc == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
