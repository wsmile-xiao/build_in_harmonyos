// kbd 2.9.0 消费者测试：以工具使用者身份运行包内交付的 kbd 命令行工具，
// 断言 --version 行为（退出码与版本输出），验证二进制在 OHOS 上可执行。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef KBD_BIN_DIR
#define KBD_BIN_DIR "."
#endif

static int g_failures = 0;

static void check(int cond, const char *msg)
{
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", msg);
    if (!cond)
        g_failures++;
}

static int run_tool(const char *tool, char *out, size_t outsz)
{
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s/%s --version 2>&1", KBD_BIN_DIR, tool);
    FILE *f = popen(cmd, "r");
    if (!f)
        return -1;
    size_t n = fread(out, 1, outsz - 1, f);
    out[n] = '\0';
    int rc = pclose(f);
    return rc;
}

int main(void)
{
    char out[512] = {0};
    int rc;

    rc = run_tool("loadkeys", out, sizeof(out));
    check(rc == 0, "loadkeys --version exits 0");
    check(strlen(out) > 0, "loadkeys --version prints version banner");

    memset(out, 0, sizeof(out));
    rc = run_tool("setfont", out, sizeof(out));
    check(rc == 0, "setfont --version exits 0");

    printf("checks=3 failures=%d\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
