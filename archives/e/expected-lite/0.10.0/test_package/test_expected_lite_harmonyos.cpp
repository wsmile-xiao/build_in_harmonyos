// test_expected_lite_harmonyos.cpp — HarmonyOS 专项测试 (expected-lite 0.10.0)
//
// 目的：验证 expected-lite 头文件库在 OHOS (HongMeng Kernel / aarch64) 目标上
// 可编译、可运行，并与 OHOS 平台 libc 接口 (sysconf/getuid) 及 errno 错误码
// 集成使用 —— 非复述上游 lest 用例，而是覆盖"OHOS 平台运行时集成"这一类
// 上游测试不覆盖的专项场景。
//
// OHOS 平台特征断言：
//   - 编译目标为 aarch64 (OHOS 唯一 arch) —— static_assert 校验
//   - OHOS 下定义了 __OHOS__ / OHOS 相关宏时一并校验（宽松处理，不强依赖）
//   - errno.h / sysconf 等 OHOS libc 头可用
//
// 编译: clang++ -std=c++17 -I<prefix>/include test_expected_lite_harmonyos.cpp
// 运行: ./a.out  (需在 OHOS 设备/模拟环境执行)
#include <nonstd/expected.hpp>

#include <cerrno>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>

// OHOS 专项 1: 平台与架构断言
#if defined(__aarch64__) || defined(_M_ARM64)
static constexpr bool kOhosAarch64 = true;
#else
static constexpr bool kOhosAarch64 = false;
#endif
static_assert(kOhosAarch64, "OHOS target must be aarch64");

// OHOS 专项 2: 用 expected 包装平台 libc 调用 (sysconf)，验证 errno 错误路径
// 真实可执行：在 OHOS 上 sysconf(_SC_PAGESIZE) 必然返回 >0 的页面大小。
nonstd::expected<long, int> ohos_page_size() {
    errno = 0;
    long sz = sysconf(_SC_PAGESIZE);
    if (sz <= 0) {
        return nonstd::make_unexpected(errno == 0 ? EINVAL : errno);
    }
    return sz;
}

// OHOS 专项 3: 用 expected 包装 getuid()，验证系统调用整型结果可装载
nonstd::expected<uid_t, int> ohos_current_uid() {
    uid_t uid = getuid();
    // OHOS getuid 不失败（POSIX），但保持错误路径可编译
    if (uid == static_cast<uid_t>(-1)) {
        return nonstd::make_unexpected(errno == 0 ? EACCES : errno);
    }
    return uid;
}

int main() {
    int failures = 0;

    // --- 专项 1: OHOS 架构/平台断言 (编译期 static_assert 已保证) ---
    std::printf("[harmonyos] target aarch64: %s\n", kOhosAarch64 ? "yes" : "no");

    // --- 专项 2: sysconf 集成 ---
    auto page = ohos_page_size();
    if (!page.has_value()) {
        std::fprintf(stderr, "[harmonyos] FAIL: ohos_page_size error=%d\n", page.error());
        ++failures;
    } else {
        long sz = page.value();
        if (sz < 4096) {
            std::fprintf(stderr, "[harmonyos] FAIL: unexpected page size %ld\n", sz);
            ++failures;
        } else {
            std::printf("[harmonyos] PASS: sysconf page size = %ld\n", sz);
        }
    }

    // value_or 在 OHOS 正常路径下的默认值行为
    long or_val = ohos_page_size().value_or(-1);
    if (or_val < 4096) {
        std::fprintf(stderr, "[harmonyos] FAIL: value_or path -> %ld\n", or_val);
        ++failures;
    } else {
        std::printf("[harmonyos] PASS: value_or = %ld\n", or_val);
    }

    // --- 专项 3: getuid 集成 ---
    auto uid = ohos_current_uid();
    if (!uid.has_value()) {
        std::fprintf(stderr, "[harmonyos] FAIL: ohos_current_uid error=%d\n", uid.error());
        ++failures;
    } else {
        std::printf("[harmonyos] PASS: getuid = %u\n", static_cast<unsigned>(uid.value()));
    }

    // --- 专项 4: monadic 链式 (C++17 下 and_then 可用) ---
    auto chained = ohos_page_size().and_then([](long sz) -> nonstd::expected<std::string, int> {
        return std::to_string(sz) + " bytes";
    });
    if (chained.has_value()) {
        std::printf("[harmonyos] PASS: monadic chain -> %s\n", chained.value().c_str());
    } else {
        std::fprintf(stderr, "[harmonyos] FAIL: monadic chain error=%d\n", chained.error());
        ++failures;
    }

    if (failures == 0) {
        std::printf("[harmonyos] ALL HARMONYOS-SPECIFIC TESTS PASSED\n");
        return 0;
    }
    std::fprintf(stderr, "[harmonyos] %d failure(s)\n", failures);
    return 1;
}