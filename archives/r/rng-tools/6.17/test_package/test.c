#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Consumer test for rng-tools 6.17 (R34: 真实执行被测程序并断言行为).
 *
 * rng-tools 交付两个可执行文件（无库），本测试直接驱动它们：
 *   1. rngtest 喂 /dev/zero：全零块必须被 FIPS-140-2 检测拒绝
 *      （退出码非 0，且输出含 FIPS 报告）——验证 rngtest 核心功能
 *   2. rngtest 喂 /dev/urandom：输出 FIPS 检测报告（通常通过）
 *   3. rngd -v：退出码 0 且打印 rng-tools 版本串——验证 rngd 可执行
 */

static int run_capture(const char *cmd, char *out, size_t outsz)
{
    FILE *f = popen(cmd, "r");
    size_t n;
    int rc;

    if (!f)
        return -1;
    n = fread(out, 1, outsz - 1, f);
    out[n] = '\0';
    rc = pclose(f);
    if (rc == -1)
        return -1;
    /* popen/pclose 返回 wait 状态：正常退出(0)时 rc==0，其余视为非零 */
    return rc ? 1 : 0;
}

int main(void)
{
    char buf[4096];
    int rc;

    /* --- 1) rngtest 必须拒绝全零流（FIPS-140-2 检测真的在工作） --- */
    rc = run_capture("rngtest -c 1 < /dev/zero 2>&1", buf, sizeof buf);
    if (rc != 1) {
        fprintf(stderr,
                "FAIL: rngtest accepted all-zero input (rc=%d) — FIPS check broken\n",
                rc);
        return 1;
    }
    if (!strstr(buf, "FIPS")) {
        fprintf(stderr, "FAIL: rngtest output lacks FIPS report:\n%s\n", buf);
        return 1;
    }

    /* --- 2) rngtest 对真实随机源输出结构化 FIPS 报告 --- */
    rc = run_capture("rngtest -c 1 < /dev/urandom 2>&1", buf, sizeof buf);
    if (rc < 0) {
        fprintf(stderr, "FAIL: rngtest on /dev/urandom could not run\n");
        return 1;
    }
    if (!strstr(buf, "FIPS")) {
        fprintf(stderr, "FAIL: rngtest urandom run lacks FIPS report:\n%s\n", buf);
        return 1;
    }

    /* --- 3) rngd -v 打印版本并成功退出 --- */
    rc = run_capture("rngd -v 2>&1", buf, sizeof buf);
    if (rc != 0) {
        fprintf(stderr, "FAIL: rngd -v exited with rc=%d:\n%s\n", rc, buf);
        return 1;
    }
    if (!strstr(buf, "rng")) {
        fprintf(stderr, "FAIL: rngd -v output lacks version string:\n%s\n", buf);
        return 1;
    }

    printf("test rng-tools 6.17: OK (rngtest FIPS reject/accept + rngd version)\n");
    return 0;
}
