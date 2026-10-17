// Consumer tests for usbrelay 1.0 on HarmonyOS PC (DCTTECH/UCREATEFUN relay driver).
// 真实编译+链接 libusbrelay.so 并调用公开 C API 断言行为：
//   A1 libusbrelay_version() 返回非空版本串；
//   A2 enumerate_relay_boards() 可调用、无崩溃、计数与 get_relay_board_count() 一致
//      （OHOS 无已连接继电器板 + hidraw 数据面权限缺口 → 期望值 0，属如实收口）；
//   A3 find_board() 对不存在序列号返回 NULL；
//   A4 operate_relay() 对不存在路径返回负值错误；
//   A5 shutdown() 正常返回（资源清理路径不崩）。
// 任一失败 → 非零退出 → ctest FAIL。

#include <libusbrelay.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    int failures = 0;

    // A1 版本 API
    const char *ver = libusbrelay_version();
    if (ver && strlen(ver) > 0)
        printf("PASS: A1 libusbrelay_version() = \"%s\"\n", ver);
    else { printf("FAIL: A1 version string empty\n"); ++failures; }

    // A2 枚举路径（含 hidapi 数据面调用链）不崩溃，计数一致
    int n = enumerate_relay_boards("USBRELAY", 0, 0);
    int c = get_relay_board_count();
    if (n >= 0 && n == c)
        printf("PASS: A2 enumerate=%d count=%d (consistent, no crash)\n", n, c);
    else { printf("FAIL: A2 enumerate=%d count=%d\n", n, c); ++failures; }

    // A3 未命中序列号
    relay_board *b = find_board("FFFFF", 0);
    if (b == NULL)
        printf("PASS: A3 find_board(FFFFF) == NULL\n");
    else { printf("FAIL: A3 unexpected board found\n"); ++failures; }

    // A4 不存在路径的操作必须报错（不得静默成功）
    int r = operate_relay("/dev/does-not-exist", 1, 1, 0);
    if (r < 0)
        printf("PASS: A4 operate_relay(bad path) = %d (<0)\n", r);
    else { printf("FAIL: A4 operate_relay returned %d (expected <0)\n", r); ++failures; }

    // A5 清理路径
    shutdown();
    printf("PASS: A5 shutdown() returned cleanly\n");

    printf("SUMMARY: %s (%d failures)\n", failures == 0 ? "ALL PASS" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
