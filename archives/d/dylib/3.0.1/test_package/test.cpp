#include <cstdio>
#include <string>

#include "dylib.hpp"

/*
 * Real HiLogPrint API (OHOS hilog, /system/lib64/platformsdk/libhilog.so):
 *   int HiLogPrint(LogType type, LogLevel level, unsigned int domain,
 *                  const char *tag, const char *fmt, ...);
 * It is a variadic function, so the consumer-facing prototype must carry the
 * trailing ellipsis and match argument order exactly; a fixed 4-arg prototype
 * would be a mismatched call type (undefined behavior).
 * Contract (OHOS docs): returns 0 or a larger value on success, a value
 * smaller than 0 otherwise. LOG_WARN/5 is used so the call is accepted by the
 * platform default minimum log level, and the assertion follows the contract
 * instead of relying on log filtering.
 */
int main() {
    // 消费者视角：真实加载 OHOS 系统动态库并调用导出符号（R34：必须实质调用被测包 API）
    dylib::library lib("/system/lib64/platformsdk/libhilog.so",
                       dylib::decorations::none());
    if (!lib.native_handle()) {
        printf("dylib 3.0.1 consumer test FAILED: dlopen libhilog failed\n");
        return 1;
    }

    auto hilog_print = lib.get_function<int(int, int, unsigned int, const char *, const char *, ...)>(
        "HiLogPrint");
    if (!hilog_print) {
        printf("dylib 3.0.1 consumer test FAILED: HiLogPrint symbol not found\n");
        return 1;
    }
    int rc = hilog_print(0 /* LOG_APP */, 5 /* LOG_WARN */, 0x0001 /* domain */,
                         "DYLIB_TEST_PACKAGE", "consumer call %s", "from dylib");
    if (rc < 0) {
        printf("dylib 3.0.1 consumer test FAILED: HiLogPrint returned %d\n", rc);
        return 1;
    }
    printf("dylib 3.0.1 consumer test PASSED (HiLogPrint rc=%d)\n", rc);
    return 0;
}