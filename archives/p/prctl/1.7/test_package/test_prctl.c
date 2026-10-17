/*
 * test_prctl.c — prctl 1.7 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   - popen 内存管道直读，**不使用 /tmp**（OHOS 上只读）
 *   - 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *     一律判 FAIL（popen 经 /bin/sh 中转，信号死亡被转写成 128+signum）
 *   - 循环读到 EOF 再 pclose；expect() 计数而非 assert()
 *
 * ★ 平台能力分级（本包判据的核心，也是本 PR 一次真实踩坑后的修正）：
 *   `--unaligned` / `--fpemu` 在上游是 **ia64 专有**操作，Linux 文档亦如此标注，
 *   但**内核是否真的返回 EINVAL 取决于具体内核**：
 *     · 本地 Ubuntu aarch64 (WSL + qemu) 内核 → `prctl(PR_SET_UNALIGN, …)`
 *       返回 EINVAL，工具打印 "This platform does not implement …" 并退出 1；
 *     · OpenHarmony CI worker 内核 → **同一二进制成功执行**该设置（退出 0，
 *       `-v` 下回显 `Set "unaligned" to "silent"`）。
 *   把本地观测到的"必然失败"写死进断言，会让 CI 上 10 条断言集体失败 ——
 *   这是**判据自身的缺陷**，不是被测程序缺陷。
 *   因此对平台专有选项，判据写成**运行时分级**（覆盖同一不变量：
 *   「合法取值必须得到明确结果，不得静默通过」）：
 *     · 平台不实现 → 必须打印明确的 "does not implement" 错误且退出非 0；
 *     · 平台实现   → 退出 0 且 `-v` 必须回显 `Set "<feat>" to "<val>"`。
 *   而**非法取值回落用法**在所有平台上都必须成立，作为稳定基线断言。
 *
 *   `--mcekill` 是架构无关操作，其可用性同样依赖内核 —— 先用 `-q` 探测平台是否
 *   列出该操作（显式探测，不假定）；列出才断言 `Set "mcekill" to "…"`，否则打印
 *   [SKIP] 并**显式说明原因**（静默跳过会把"没跑"伪装成"跑过了"）。
 *
 * 用法: test_prctl <prctl 可执行文件路径>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static int g_pass = 0, g_fail = 0;

static const char *USAGE_MARK = "Usage: prctl [-v] [-h|--help] [--version]";

static void expect(int cond, const char *what, const char *detail)
{
    if (cond) {
        g_pass++;
        printf("  [PASS] %s\n", what);
    } else {
        g_fail++;
        printf("  [FAIL] %s%s%s\n", what,
               detail && *detail ? " — " : "", detail && *detail ? detail : "");
    }
    fflush(stdout);
}

static void expect_contains(const char *label, const char *out, const char *needle)
{
    char what[320], d[400];
    snprintf(what, sizeof(what), "%s: 输出含 \"%s\"", label, needle);
    if (strstr(out, needle) != NULL) {
        expect(1, what, "");
    } else {
        snprintf(d, sizeof(d), "实际输出: %.240s", out);
        expect(0, what, d);
    }
}

static int run_capture(const char *args, char *buf, size_t cap)
{
    char cmd[4096];
    FILE *fp;
    size_t n = 0, got;
    int rc, killed, code;

    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", g_bin, args);
    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp)
        return -1;
    while (n < cap - 1 && (got = fread(buf + n, 1, cap - 1 - n, fp)) > 0)
        n += got;
    buf[n] = '\0';
    rc = pclose(fp);
    if (rc == -1)
        return -1;
    killed = !WIFEXITED(rc);
    code = killed ? -1 : WEXITSTATUS(rc);
    if (killed || code == 126 || code == 127 || code >= 128)
        return -1;
    return code;
}

/* 用例：退出码 + 必须出现的字面量；can_fail_soft 由调用方决定 */
static void case_expect(const char *args, int want_rc,
                        const char *const *needles, int n_needles,
                        int want_usage)
{
    static char buf[32768];
    char label[256], d[160];
    int rc, i;

    printf("── prctl %s\n", args);
    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "进程无法正常执行（pclose==-1 / 被信号杀死 / 126,127,>=128）", "");
        return;
    }
    snprintf(label, sizeof(label), "退出码 (期望 %d)", want_rc);
    snprintf(d, sizeof(d), "实际 %d", rc);
    expect(rc == want_rc, label, rc == want_rc ? "" : d);

    for (i = 0; i < n_needles; i++)
        expect_contains("内容", buf, needles[i]);

    if (want_usage)
        expect_contains("用法块", buf, USAGE_MARK);

    expect(strlen(buf) > 0, "有输出（非静默失败）", "");
}

/* 平台专有选项的**运行时分级**断言：
 *   平台不实现 → 必须打印 "does not implement set_<feat> prctl feature" 且退出非 0
 *   平台实现   → 退出 0 且 -v 必须回显 `Set "<feat>" to "<val>"`
 * 两条分支覆盖同一不变量，且不假定任何一端（本地内核与 CI 真机行为可能不同）。 */
static void case_platform_option(const char *feat, const char *val)
{
    static char buf[16384];
    char args[192], notimpl[128], conf[128], label[288], d[420];
    int rc;

    snprintf(args, sizeof(args), "--%s=%s -v", feat, val);
    snprintf(notimpl, sizeof(notimpl), "does not implement set_%s prctl feature", feat);
    snprintf(conf, sizeof(conf), "Set \"%s\" to \"%s\"", feat, val);

    printf("── prctl %s\n", args);
    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        snprintf(label, sizeof(label), "--%s=%s: 进程无法正常执行", feat, val);
        expect(0, label, "");
        return;
    }

    if (rc != 0) {
        /* 分支 A：平台不实现 —— 必须明确报错，不得静默成功 */
        snprintf(label, sizeof(label),
                 "--%s=%s 平台不实现 → 退出码非 0（实际 %d）", feat, val, rc);
        expect(1, label, "");
        snprintf(label, sizeof(label), "--%s=%s 打印明确的平台不实现错误", feat, val);
        if (strstr(buf, notimpl) != NULL) {
            expect(1, label, "");
        } else {
            snprintf(d, sizeof(d), "实际输出: %.320s", buf);
            expect(0, label, d);
        }
        printf("  [INFO] 平台不实现 --%s（退出码 %d）\n", feat, rc);
    } else {
        /* 分支 B：平台实现 —— -v 必须回显设置结果 */
        snprintf(label, sizeof(label), "--%s=%s 平台实现 → 退出码 0", feat, val);
        expect(1, label, "");
        snprintf(label, sizeof(label), "--%s=%s 回显 \"%s\"", feat, val, conf);
        if (strstr(buf, conf) != NULL) {
            expect(1, label, "");
        } else {
            snprintf(d, sizeof(d), "实际输出: %.320s", buf);
            expect(0, label, d);
        }
        snprintf(label, sizeof(label), "--%s=%s 成功时不报平台不实现", feat, val);
        expect(strstr(buf, notimpl) == NULL, label,
               "同时出现成功回显与平台不实现错误");
        printf("  [INFO] 平台实现 --%s\n", feat);
    }
}

int main(int argc, char **argv)
{
    static char buf[32768];
    char label[256];
    int rc, have_mcekill = 0;

    static const char *invalid_opt[] = { "invalid option" };
    static const char *version[] = { "prctl version 1.7" };
    static const char *qheader[] = { "Current settings for supported prctl operations:" };

    if (argc < 2) {
        fprintf(stderr, "usage: %s <prctl-binary>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    printf("=== prctl 1.7 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);

    /* ── 1. 版本与用法 ── */
    case_expect("--version", 0, version, 1, 0);
    case_expect("-h", 0, version, 1, 1);
    case_expect("--help", 0, version, 1, 1);

    /* 无参数与仅有 -v（无动作）都必须报用法并非 0 退出 */
    case_expect("", 1, version, 1, 1);
    case_expect("-v", 1, version, 1, 1);

    /* 用法块必须完整列出三类操作（-q 之外的全部选项） */
    {
        static char ub[16384];
        rc = run_capture("--help", ub, sizeof(ub));
        if (rc >= 0) {
            expect_contains("用法块列 unaligned", ub, "--unaligned=");
            expect_contains("用法块列 fpemu", ub, "--fpemu=");
            expect_contains("用法块列 mcekill", ub, "--mcekill=");
            expect_contains("用法块列 -q", ub, "<-q|<options>>");
        }
    }

    /* ── 2. -q 查询：header + 平台能力探测 ── */
    printf("── prctl -q（查询当前设置 + 平台能力探测）\n");
    rc = run_capture("-q", buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "-q 无法执行", "");
    } else {
        expect(rc == 0, "-q 退出码 (期望 0)", "");
        expect_contains("-q", buf, qheader[0]);
        have_mcekill = (strstr(buf, "mcekill") != NULL);
        expect(have_mcekill, "平台列出 mcekill 操作（架构无关操作，预期存在）",
               "未列出 —— 后续 set 用例将显式跳过");
        printf("  [INFO] mcekill 支持 = %s\n", have_mcekill ? "是" : "否");
    }

    case_expect("-v -q", 0, qheader, 1, 0);

    /* ── 3. 平台专有操作 --unaligned / --fpemu：运行时分级断言 ──
     *   不假定"必然失败"（本地内核失败、OHOS 内核成功），只断言不变量：
     *   合法取值必须得到明确结果 —— 要么明确报平台不实现并非 0 退出，
     *   要么成功并在 -v 下回显设置结果。 */
    case_platform_option("unaligned", "silent");
    case_platform_option("unaligned", "signal");
    case_platform_option("unaligned", "default");
    case_platform_option("fpemu", "silent");
    case_platform_option("fpemu", "signal");

    /* ── 4. 非法取值：必须回落用法并非 0 退出 ── */
    case_expect("--unaligned=bogus", 1, NULL, 0, 1);
    case_expect("--fpemu=bogus", 1, NULL, 0, 1);
    case_expect("--mcekill=bogus", 1, NULL, 0, 1);

    /* ── 5. 非法选项：必须报 invalid option 并非 0 退出 ── */
    case_expect("--nope", 1, invalid_opt, 1, 0);
    case_expect("-Z", 1, invalid_opt, 1, 0);
    case_expect("--mcekill", 1, invalid_opt, 1, 0);   /* 缺 '=' 也要被拒 */

    /* ── 6. mcekill 设置路径（平台能力分级）── */
    if (!have_mcekill) {
        printf("  [SKIP] 平台 -q 未列出 mcekill，跳过 3 个 set 用例\n");
        printf("         （显式跳过：内核不支持 PR_MCE_KILL 时该路径不可达，\n");
        printf("           而非被测程序缺陷；跳过原因已记录于此）\n");
    } else {
        static const char *vals[] = { "early", "late", "default" };
        int i;
        for (i = 0; i < 3; i++) {
            char args[128], want[64];
            snprintf(args, sizeof(args), "--mcekill=%s -v", vals[i]);
            snprintf(want, sizeof(want), "Set \"mcekill\" to \"%s\"", vals[i]);
            printf("── prctl %s\n", args);
            rc = run_capture(args, buf, sizeof(buf));
            if (rc < 0) {
                expect(0, "mcekill set 用例无法执行", "");
                continue;
            }
            snprintf(label, sizeof(label), "--mcekill=%s -v 退出码 (期望 0)", vals[i]);
            expect(rc == 0, label, rc == 0 ? "" : "非 0");
            {
                char what[192], d[320];
                snprintf(what, sizeof(what), "回显 \"%s\"", want);
                if (strstr(buf, want) != NULL) {
                    expect(1, what, "");
                } else {
                    snprintf(d, sizeof(d), "实际输出: %.240s", buf);
                    expect(0, what, d);
                }
            }
            {
                char what[160];
                snprintf(what, sizeof(what), "--mcekill=%s 不报 Failed to", vals[i]);
                expect(strstr(buf, "Failed to") == NULL, what,
                       strstr(buf, "Failed to") ? "内核拒绝了该设置" : "");
            }
        }
    }

    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
