/*
 * razercfg 0.44 test_package 消费者测试
 *
 * 上游无测试（R51 清点：无 test 目录、CMakeLists 无 enable_testing/add_test）。
 * 本测试覆盖 librazer 核心库可链接性与纯函数 API（不依赖 USB 硬件）：
 *   - razer_strlcpy: 安全字符串拷贝（边界/截断语义）
 *   - razer_utf16_strlen: UTF-16 字符串长度
 *   - razer_ascii_to_utf16: ASCII → UTF-16 转换
 *
 * 同时执行 razerd -v 验证守护进程二进制可运行（test_package conanfile.py 中）。
 *
 * 注意：librazer.h 要求定义 RAZERCFG_BUILD 宏（内部库保护），
 * 本测试源文件在 include 前通过 #define RAZERCFG_BUILD 注入（见下方）。
 *
 * R40 深度适配标注：razercfg 属外设（Razer USB 设备）配置工具，核心能力
 * 依赖 libusb 与真实 USB 硬件交互（HAL/驱动接口）。CI 无硬件环境，本测试
 * 仅覆盖不依赖硬件的库级纯函数 API 与守护进程可运行性；真实设备配置路径
 * （EUI64/DPI/按键映射等）需在有 Razer 硬件的真机上人工确认适配完整性。
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>

#define RAZERCFG_BUILD
#include <librazer/librazer.h>

int main(void)
{
    char buf[16];

    /* razer_strlcpy: 正常拷贝 */
    memset(buf, 0xAA, sizeof(buf));
    razer_strlcpy(buf, "hello", sizeof(buf));
    assert(strcmp(buf, "hello") == 0);
    assert(strlen(buf) == 5);

    /* razer_strlcpy: 目标过小截断，保证 NUL 结尾 */
    memset(buf, 0xBB, sizeof(buf));
    razer_strlcpy(buf, "this is a very long string that exceeds buffer", sizeof(buf));
    assert(strlen(buf) == sizeof(buf) - 1);
    assert(buf[sizeof(buf) - 1] == '\0');

    /* razer_strlcpy: 空字符串 */
    memset(buf, 0xCC, sizeof(buf));
    razer_strlcpy(buf, "", sizeof(buf));
    assert(buf[0] == '\0');

    /* razer_utf16_strlen: UTF-16 长度 */
    {
        razer_utf16_t u16[] = { 'a', 'b', 'c', 0 };
        assert(razer_utf16_strlen(u16) == 3);
    }

    /* razer_ascii_to_utf16: ASCII → UTF-16 */
    {
        razer_utf16_t dest[8];
        razer_ascii_to_utf16(dest, 8, "Razer");
        assert(razer_utf16_strlen(dest) == 5);
        assert(dest[0] == 'R' && dest[4] == 'r');
        assert(dest[5] == 0);
    }

    printf("test_razercfg: ALL ASSERTIONS PASSED (%zu asserts, 6 checks)\n", (size_t)9);
    return 0;
}
