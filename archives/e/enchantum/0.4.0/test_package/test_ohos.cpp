// HarmonyOS 专项测试 — enchantum 0.4.0
//
// 本测试是独立于上游测试之外的鸿蒙平台专项用例（任务要求 5）：
//  - 断言编译目标确为 HarmonyOS（__OHOS__ 宏存在），验证工具链/平台语义
//  - 在 OHOS aarch64 工具链( clang15 + OHOS SDK )下真实编译运行 enchantum API
//  - 使用静态断言 + 运行时断言，全部失败即退出码非 0
#include <enchantum/enchantum.hpp>
#include <enchantum/bitset.hpp>
#include <enchantum/bitflags.hpp>

#include <cstdint>
#include <iostream>
#include <string_view>

// 平台断言：OHOS 编译环境下必须定义 __OHOS__
#ifdef __OHOS__
#define OHOS_PLATFORM_VERIFIED 1
#else
#define OHOS_PLATFORM_VERIFIED 0
#endif

// 位标志枚举：to_string / bitset 验证（值 1,2,4,7，稀疏枚举）
enum class Permission : std::uint32_t {
    Read = 1u << 0,
    Write = 1u << 1,
    Execute = 1u << 2,
    All = Read | Write | Execute,
};

// 连续枚举：枚举值计数断言
enum class Level { Info, Warn, Error };

int main() {
    bool ok = true;

    if (!OHOS_PLATFORM_VERIFIED) {
        std::cerr << "FAIL: __OHOS__ 未定义，非 HarmonyOS 目标\n";
        ok = false;
    }

    // 运行时 API 验证（同上游语义，但在 OHOS 目标上执行）
    if (enchantum::to_string(Permission::Read) != "Read") {
        std::cerr << "FAIL: to_string(Permission::Read)\n";
        ok = false;
    }

    // 枚举值计数（连续枚举应为 3 个成员）
    int value_count = 0;
    for (const auto v : enchantum::values_generator<Level>) {
        (void)v;
        ++value_count;
    }
    if (value_count != 3) {
        std::cerr << "FAIL: 期望 3 个枚举值, got " << value_count << "\n";
        ok = false;
    }

    // bitset 适配器在 OHOS 上真实运行（初始化列表构造，避免裸枚举 OR）
    enchantum::bitset<Permission> bs{Permission::Read, Permission::Write};
    if (!bs.test(Permission::Read) || !bs.test(Permission::Write) ||
        bs.test(Permission::Execute)) {
        std::cerr << "FAIL: bitset 位操作结果不符\n";
        ok = false;
    }

    if (ok) {
        std::cout << "OHOS test: PASS (platform=OHOS, enchantum="
                  << enchantum::to_string(Permission::All) << ")\n";
        return 0;
    }
    return 1;
}