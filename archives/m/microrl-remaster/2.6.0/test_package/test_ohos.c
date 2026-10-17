/* HarmonyOS 专项测试 — microrl-remaster 2.6.0
 * 目标：验证 microrl 在 OHOS (aarch64-linux-ohos, clang 15) 工具链下
 * 可编译、可链接、可运行，且公开 API 行为正确。本文件是真正的 HarmonyOS
 * 专项用例（区别于上游交互式演示程序）：
 *   - 编译目标固定为 OHOS aarch64（由 CMakeToolchain/ohos-aarch64 profile 保证）
 *   - 断言编译目标架构为 aarch64（__aarch64__），验证平台识别路径
 *   - 真实调用公开 API：microrl_init / microrl_set_execute_callback /
 *     microrl_set_prompt / microrl_processing_input / microrl_get_version
 *   - 断言命令解析（多 token）、版本号、重复调用稳定性，任一断言失败非零退出
 */
#include <microrl/microrl.h>

#include <stdio.h>
#include <string.h>

static int g_exec_called = 0;
static int g_exec_argc = 0;
static char g_exec_argv0[32] = {0};
static char g_exec_argv1[32] = {0};

static int out_fn(struct microrl* mrl, const char* str)
{
    (void)mrl;
    (void)str;
    return 0;
}

static int exec_fn(struct microrl* mrl, int argc, const char* const* argv)
{
    (void)mrl;
    g_exec_called = 1;
    g_exec_argc = argc;
    if (argc > 0 && argv[0]) {
        snprintf(g_exec_argv0, sizeof(g_exec_argv0), "%s", argv[0]);
    }
    if (argc > 1 && argv[1]) {
        snprintf(g_exec_argv1, sizeof(g_exec_argv1), "%s", argv[1]);
    }
    return 0;
}

static int expect_platform(void)
{
#if defined(__aarch64__)
    printf("PLATFORM: __aarch64__ detected -- OHOS arm64 识别正确\n");
    return 0;
#else
    printf("PLATFORM: %s -- 非预期（OHOS PC 应为 aarch64）\n",
#if defined(__arm__)
           "__arm__"
#else
           "unknown arch"
#endif
    );
    return 1;
#endif
}

int main(void)
{
    microrl_t mrl;
    int rc = 0;

    if (expect_platform() != 0) {
        rc = 1;
    }

    /* 版本号：2.6.0 -> 0x020600 */
    if (microrl_get_version() != 0x020600u) {
        printf("FAIL: microrl_get_version()=0x%06x, expected 0x020600\n",
               (unsigned)microrl_get_version());
        rc = 1;
    }

    if (microrl_init(&mrl, out_fn, exec_fn) != microrlOK) {
        printf("FAIL: microrl_init()\n");
        return 1;
    }
    if (microrl_set_execute_callback(&mrl, exec_fn) != microrlOK) {
        printf("FAIL: microrl_set_execute_callback()\n");
        rc = 1;
    }
    if (microrl_set_prompt(&mrl, (char*)"ohos> ") != microrlOK) {
        printf("FAIL: microrl_set_prompt()\n");
        rc = 1;
    }

    /* 命令解析：两 token 命令，验证 execute 回调收到 argc=2, argv[0]="test" */
    const char* line = "test microrl\n";
    if (microrl_processing_input(&mrl, line, strlen(line)) != microrlOK) {
        printf("FAIL: microrl_processing_input()\n");
        rc = 1;
    }
    if (!g_exec_called || g_exec_argc != 2 ||
        strcmp(g_exec_argv0, "test") != 0 ||
        strcmp(g_exec_argv1, "microrl") != 0) {
        printf("FAIL: exec callback argc=%d argv0='%s' argv1='%s'\n",
               g_exec_argc, g_exec_argv0, g_exec_argv1);
        rc = 1;
    }

    /* 清屏 API（2.6.0 新增）不应破坏实例状态 */
    if (microrl_clear_terminal(&mrl) != microrlOK) {
        printf("FAIL: microrl_clear_terminal()\n");
        rc = 1;
    }

    /* 二次输入：同一实例稳定工作（无状态破坏） */
    g_exec_called = 0;
    const char* line2 = "quit\n";
    if (microrl_processing_input(&mrl, line2, strlen(line2)) != microrlOK) {
        printf("FAIL: second microrl_processing_input()\n");
        rc = 1;
    }
    if (!g_exec_called || g_exec_argc != 1 || strcmp(g_exec_argv0, "quit") != 0) {
        printf("FAIL: second exec callback argc=%d argv0='%s'\n",
               g_exec_argc, g_exec_argv0);
        rc = 1;
    }

    if (rc == 0) {
        printf("test microrl-remaster OHOS: ALL PASS (version 0x020600, argv0=%s argv1=%s)\n",
               g_exec_argv0, g_exec_argv1);
    }
    return rc;
}
