// HarmonyOS 专项测试 — phonon 4.12.0
//
// 本测试是鸿蒙平台专项用例，验证 OHOS 适配后 phonon 库的行为：
// 1) 编译目标确为 HarmonyOS（__OHOS__ 宏存在）
// 2) phononVersion() 在 OHOS 上返回有效版本字符串
// 3) BackendCapabilities 在无后端插件时返回空列表（预期行为，不崩溃）
// 4) 音频输出设备枚举在 OHOS 上正常工作（空列表，无插件）
#include <phonon/phononnamespace.h>
#include <phonon/backendcapabilities.h>
#include <QString>
#include <QStringList>
#include <cstdio>
#include <cstring>

// 平台断言：OHOS 编译环境下必须定义 __OHOS__
#ifdef __OHOS__
#define OHOS_PLATFORM_VERIFIED 1
#else
#define OHOS_PLATFORM_VERIFIED 0
#endif

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        std::fprintf(stderr, "[FAIL] %s @%d\n", msg, __LINE__); \
        failures++; \
    } else { \
        std::fprintf(stdout, "[PASS] %s\n", msg); \
    } \
} while (0)

int main() {
    // 1) 平台验证：确认编译目标为 HarmonyOS
    CHECK(OHOS_PLATFORM_VERIFIED, "OHOS 平台宏验证 (__OHOS__ defined)");

    // 2) 库版本字符串：验证 libphonon4qt6.so 正确加载且版本非空
    const char *ver = Phonon::phononVersion();
    CHECK(ver != nullptr && ver[0] != '\0', "phononVersion() 返回非空字符串");
    if (ver) {
        std::fprintf(stdout, "  Phonon version: %s\n", ver);
        CHECK(std::strlen(ver) > 0, "phononVersion() 长度 > 0");
    }

    // 3) 后端能力枚举：OHOS 无后端插件时应返回空列表，不崩溃
    const QStringList mimeTypes =
        Phonon::BackendCapabilities::availableMimeTypes();
    CHECK(mimeTypes.isEmpty(), "BackendCapabilities MIME types 为空（无后端插件，预期行为）");
    std::fprintf(stdout, "  MIME types count: %lld\n",
                  static_cast<long long>(mimeTypes.size()));

    const auto audioOutputs =
        Phonon::BackendCapabilities::availableAudioOutputDevices();
    CHECK(audioOutputs.isEmpty(), "BackendCapabilities 音频输出设备为空（无后端插件，预期行为）");
    std::fprintf(stdout, "  Audio output devices count: %lld\n",
                  static_cast<long long>(audioOutputs.size()));

    // 4) 静态 API 调用验证：确保库的内部表/函数指针表正确初始化
    // phononVersion() 来自 libphonon4qt6.so 的导出符号，调用成功即证明
    // ELF 动态链接在 OHOS 上工作正常（DT_SONAME / DT_NEEDED 路径正确）
    CHECK(ver != nullptr, "动态链接验证：phononVersion() 符号已解析");

    if (failures == 0) {
        std::fprintf(stdout, "\nphonon OHOS 专项测试: ALL CHECKS PASSED\n");
        return 0;
    }
    std::fprintf(stderr, "\nphonon OHOS 专项测试: %d check(s) FAILED\n", failures);
    return 1;
}
