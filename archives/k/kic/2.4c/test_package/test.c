/*
 * test.c — kic 2.4c 鸿蒙消费者端到端测试 (R34 真实产物执行)
 *
 * 在 OHOS (aarch64) 环境实际执行被测包产出的两个命令行工具，验证
 * CIF → kic → CIF 转换链路（kic GUI 本体需 X 显示，OHOS 无显示环境，
 * 与上游一致的做法是使用其附带的转换 CLI 验证核心库 cd/convert 功能）：
 *   1. ciftokic  good.cif        → 期望 exit 0 且生成 Root/Symbol1 单元文件
 *   2. kictocif  Root (stdin)    → 期望 exit 0 且生成 Root.cif，内容含
 *                                  "B 100 100 50 50"（与输入几何一致）
 * 均为真实进程执行（fork/exec），非打印式空壳测试。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *SAMPLE_CIF =
    "(test);\n"
    "DS 1 10 1;\n"
    "L CMF;\n"
    "B 10 10 5 5;\n"
    "DF;\n"
    "C 1;\n"
    "E;\n";

static int g_assertions = 0;

static void ok(int cond, const char *what)
{
    g_assertions++;
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", what);
    if (!cond)
        exit(1);
}

int main(void)
{
    FILE *f;
    int rc;

    /* ---- 用例 1: ciftokic CIF -> kic 单元文件 ---- */
    f = fopen("good.cif", "w");
    ok(f != NULL, "创建样例 CIF 输入文件");
    fputs(SAMPLE_CIF, f);
    fclose(f);

    rc = system(CIFTOKIC " good.cif > /dev/null 2>&1");
    ok(rc == 0, "ciftokic 转换样例 CIF（exit 0）");

    f = fopen("Root", "r");
    ok(f != NULL, "ciftokic 生成 kic 层级根单元文件 Root");
    if (f)
        fclose(f);
    f = fopen("Symbol1", "r");
    ok(f != NULL, "ciftokic 生成单元文件 Symbol1");
    if (f)
        fclose(f);

    /* ---- 用例 2: kictocif kic -> CIF 回转（鸿蒙消费者端到端） ---- */
    {
        char cmd[1024];
        char buf[256];
        int found = 0;

        snprintf(cmd, sizeof(cmd),
                 "KIC_LIB_DIR=" KIC_LIBDIR " " KICTOCIF " < root.in > /dev/null 2>&1");
        f = fopen("root.in", "w");
        ok(f != NULL, "准备 kictocif 交互输入");
        fputs("Root\n\n", f);
        fclose(f);

        rc = system(cmd);
        ok(rc == 0, "kictocif 回转 kic 单元为 CIF（exit 0）");

        f = fopen("Root.cif", "r");
        ok(f != NULL, "kictocif 生成 Root.cif");
        if (f) {
            while (fgets(buf, sizeof(buf), f))
                if (strstr(buf, "B 100 100 50 50"))
                    found = 1;
            fclose(f);
        }
        ok(found, "回转 CIF 保留原始几何 B 100 100 50 50（端到端一致）");
    }

    printf("ALL %d ASSERTIONS PASSED\n", g_assertions);
    return 0;
}
