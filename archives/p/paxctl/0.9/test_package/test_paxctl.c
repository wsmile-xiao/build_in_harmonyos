/*
 * test_paxctl.c — paxctl 0.9 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   - 全程 popen 内存管道直读，**不使用 /tmp**（OHOS 上 /tmp 只读）；
 *     需要可写文件时只用 argv[2] 传入的 scratch 目录，并先显式探测可写性。
 *   - 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *     一律判 FAIL（popen 经 /bin/sh 中转，信号死亡被转写成 128+signum）。
 *   - 循环读到 EOF 再 pclose。
 *   - expect() 计数而非 assert()（NDEBUG 下 assert 会被整体编译掉）。
 *
 * 夹具策略：**用被测程序自身的二进制副本当 ELF 夹具**。
 *   paxctl 操作的是 ELF 程序头，任何本包产出的 aarch64 ELF 都是合法输入；
 *   用 bin/paxctl 自身既避免引入外部样本，又顺带证明「产物本身是结构完好、
 *   可被工具正确解析的 ELF」。
 *
 * 12 字符的标志串布局（实测标定，每 2 字符一个槽：
 *   偶下标 = "已启用"字母，奇下标 = "已禁用"字母）：
 *     0/1  P/p  PAGEEXEC
 *     2/3  S/s  SEGMEXEC
 *     4/5  M/m  MPROTECT
 *     6/7    x  RANDEXEC
 *     8/9  E/e  EMUTRAMP
 *    10/11 R/r  RANDMMAP
 *   基准（-c 转换 + -z 复位后）恒为 "-------x----"。
 *
 * 用法: test_paxctl <paxctl 可执行文件路径> <可写 scratch 目录>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static const char *g_scratch = NULL;
static int g_pass = 0, g_fail = 0;

static const char *g_feat[12] = {
    "PAGEEXEC", "PAGEEXEC", "SEGMEXEC", "SEGMEXEC", "MPROTECT", "MPROTECT",
    "RANDEXEC", "RANDEXEC", "EMUTRAMP", "EMUTRAMP", "RANDMMAP", "RANDMMAP"
};
static const char *g_base_flags = "-------x----";

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

/* 执行 "<bin> <args>"，读 stdout+stderr；返回退出码，跑不起来返回 -1 */
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

static int path(char *out, size_t cap, const char *name)
{
    return snprintf(out, cap, "%s/%s", g_scratch, name) > 0;
}

static int copy_file(const char *src, const char *dst)
{
    FILE *in = fopen(src, "rb"), *out;
    char buf[65536];
    size_t n;
    if (!in)
        return -1;
    out = fopen(dst, "wb");
    if (!out) {
        fclose(in);
        return -1;
    }
    while ((n = fread(buf, 1, sizeof buf, in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            fclose(in);
            fclose(out);
            return -1;
        }
    }
    if (fclose(out) != 0) {
        fclose(in);
        return -1;
    }
    fclose(in);
    return 0;
}

/* 从 `- PaX flags: XXXXXXXXXXXX [path]` 里抽出 12 字符标志串 */
static int extract_flags(const char *out, char *dst, size_t cap)
{
    const char *p = strstr(out, "PaX flags:");
    const char *s, *e;
    size_t len;
    if (!p)
        return 0;
    s = p + strlen("PaX flags:");
    while (*s == ' ')
        s++;
    e = strchr(s, ' ');
    if (!e)
        return 0;
    len = (size_t)(e - s);
    if (len == 0 || len >= cap)
        return 0;
    memcpy(dst, s, len);
    dst[len] = '\0';
    return 1;
}

/* 复位夹具：复制一份干净二进制 → -c 转换 → -z 复位 */
static int reset_fixture(void)
{
    char fx[512], args[1024], buf[16384];
    if (!path(fx, sizeof(fx), "fixture"))
        return -1;
    if (copy_file(g_bin, fx) != 0)
        return -1;
    snprintf(args, sizeof(args), "-c \"%s\"", fx);
    if (run_capture(args, buf, sizeof(buf)) < 0)
        return -1;
    snprintf(args, sizeof(args), "-z \"%s\"", fx);
    if (run_capture(args, buf, sizeof(buf)) < 0)
        return -1;
    return 0;
}

/* 校验"标志串 ↔ 说明行"一致性：标志串里非 '-' 的每一位都必须有对应说明行 */
static void check_explanation(const char *out, const char *flags, const char *tag)
{
    char label[192], need[96];
    int i, bad = 0;
    for (i = 0; i < 12; i++) {
        if (flags[i] == '-')
            continue;
        snprintf(need, sizeof(need), "%s is %s", g_feat[i],
                 (i % 2 == 0) ? "enabled" : "disabled");
        if (strstr(out, need) == NULL) {
            snprintf(label, sizeof(label), "%s: 标志位 %d 的说明行 \"%s\"", tag, i, need);
            expect(0, label, "缺失");
            bad++;
            break;
        }
    }
    if (!bad) {
        snprintf(label, sizeof(label), "%s: 12 位标志串与说明行一致", tag);
        expect(1, label, "");
    }
}

/* 通用：先执行 paxctl <args> 应用改动，再单独用 -v 读取结果并断言
 *   ★ 必须是两次调用：实测 `paxctl -v -m <file>` 只查看、不应用改动
 *     （输出仍是改动前的标志串），把 -v 与修改标志放在同一次调用会得到
 *     一个"永远等于基准串"的假通过。 */
static void case_flags(const char *tag, const char *args, int want_rc,
                       const char *want_flags)
{
    static char buf[16384];
    char fx[512], full[1024], flags[64], label[256], d[320];
    int rc;

    snprintf(fx, sizeof(fx), "%s/fixture", g_scratch);
    snprintf(full, sizeof(full), "%s \"%s\"", args, fx);
    rc = run_capture(full, buf, sizeof(buf));
    if (rc < 0) {
        snprintf(label, sizeof(label), "%s: 进程无法正常执行", tag);
        expect(0, label, "");
        return;
    }
    snprintf(label, sizeof(label), "%s: 应用改动退出码 (期望 %d)", tag, want_rc);
    snprintf(d, sizeof(d), "实际 %d", rc);
    expect(rc == want_rc, label, rc == want_rc ? "" : d);

    /* 第二次调用：单独的 -v 读取 */
    snprintf(full, sizeof(full), "-v \"%s\"", fx);
    rc = run_capture(full, buf, sizeof(buf));
    if (rc < 0) {
        snprintf(label, sizeof(label), "%s: -v 读取无法正常执行", tag);
        expect(0, label, "");
        return;
    }
    if (!extract_flags(buf, flags, sizeof(flags))) {
        snprintf(label, sizeof(label), "%s: 能解析出标志串", tag);
        expect(0, label, "未找到 'PaX flags:' 行");
        return;
    }
    snprintf(label, sizeof(label), "%s: 标志串 (期望 \"%s\")", tag, want_flags);
    snprintf(d, sizeof(d), "实际 \"%s\"", flags);
    expect(strcmp(flags, want_flags) == 0, label,
           strcmp(flags, want_flags) == 0 ? "" : d);

    /* 12 字符形状 */
    {
        int ok = (strlen(flags) == 12), i;
        for (i = 0; ok && i < 12; i++)
            if (!((flags[i] >= 'A' && flags[i] <= 'Z') ||
                  (flags[i] >= 'a' && flags[i] <= 'z') || flags[i] == '-'))
                ok = 0;
        snprintf(label, sizeof(label), "%s: 标志串为 12 字符且字符集合法", tag);
        expect(ok, label, ok ? "" : flags);
    }
    check_explanation(buf, flags, tag);
}

/* 读当前夹具标志串（-v），失败返回 0 */
static int read_flags(char *flags, size_t cap)
{
    static char buf[16384];
    char fx[512], args[1024];
    snprintf(fx, sizeof(fx), "%s/fixture", g_scratch);
    snprintf(args, sizeof(args), "-v \"%s\"", fx);
    if (run_capture(args, buf, sizeof(buf)) < 0)
        return 0;
    return extract_flags(buf, flags, cap);
}

int main(int argc, char **argv)
{
    static char buf[16384];
    char fx[512], noelf[512], missing[512], flags[64], args[1024], label[256], d[256];
    int rc, i;
    static const char *PER_FLAG[][2] = {
        { "-p", "-p-----x----" }, { "-P", "P------x----" },
        { "-e", "-------x-e--" }, { "-E", "-------xE---" },
        { "-m", "-----m-x----" }, { "-M", "----M--x----" },
        { "-r", "-------x---r" }, { "-R", "-------x--R-" },
        { "-s", "---s---x----" }, { "-S", "--S----x----" },
    };

    if (argc < 3) {
        fprintf(stderr, "usage: %s <paxctl-binary> <scratch-dir>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    g_scratch = argv[2];

    printf("=== paxctl 0.9 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);
    printf("scratch   : %s\n", g_scratch);

    /* ── 0. 前置：scratch 目录必须可写（显式探测，不假定）── */
    if (!path(fx, sizeof(fx), "probe.tmp")) {
        expect(0, "scratch 路径可用", "");
        goto summary;
    }
    if (copy_file(g_bin, fx) != 0) {
        expect(0, "scratch 目录可写（复制夹具成功）", fx);
        goto summary;
    }
    expect(1, "scratch 目录可写（复制夹具成功）", "");
    remove(fx);

    /* ── 1. 用法与错误路径 ── */
    printf("── paxctl（无参数）\n");
    rc = run_capture("", buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "无参数调用无法正常执行", "");
    } else {
        snprintf(d, sizeof(d), "实际 %d", rc);
        expect(rc == 1, "无参数退出码 (期望 1)", rc == 1 ? "" : d);
        expect(strstr(buf, "usage: paxctl <options> <files>") != NULL,
               "无参数打印 usage 行", "");
        expect(strstr(buf, "PaX control v0.9") != NULL, "版本串 PaX control v0.9", "");
    }

    printf("── paxctl --help\n");
    rc = run_capture("--help", buf, sizeof(buf));
    expect(rc == 1, "--help 退出码 (期望 1：非长选项，走 usage)", "");
    expect(strstr(buf, "usage: paxctl") != NULL, "--help 打印 usage", "");

    printf("── paxctl -Z <fixture>（非法选项）\n");
    if (reset_fixture() == 0) {
        snprintf(fx, sizeof(fx), "%s/fixture", g_scratch);
        snprintf(args, sizeof(args), "-Z \"%s\"", fx);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 1, "非法选项 -Z 退出码 (期望 1)", "");
        expect(strstr(buf, "unrecognized option") != NULL,
               "非法选项报 unrecognized option", "");
    }

    /* ── 2. 文件类错误 ── */
    snprintf(missing, sizeof(missing), "%s/definitely-missing", g_scratch);
    snprintf(args, sizeof(args), "-v \"%s\"", missing);
    printf("── paxctl -v <不存在>\n");
    rc = run_capture(args, buf, sizeof(buf));
    expect(rc == 1, "不存在的文件退出码 (期望 1)", "");
    expect(strstr(buf, "No such file or directory") != NULL,
           "不存在文件报 No such file or directory", "");

    snprintf(noelf, sizeof(noelf), "%s/notelf.txt", g_scratch);
    {
        FILE *f = fopen(noelf, "wb");
        if (f) {
            fputs("this is not an ELF file\n", f);
            fclose(f);
        }
    }
    snprintf(args, sizeof(args), "-v \"%s\"", noelf);
    printf("── paxctl -v <非 ELF 文件>\n");
    rc = run_capture(args, buf, sizeof(buf));
    expect(rc == 1, "非 ELF 文件退出码 (期望 1)", "");
    expect(strstr(buf, "is not a valid ELF executable") != NULL,
           "非 ELF 文件报 not a valid ELF executable", "");

    /* ── 3. 未转换的 ELF：应提示 try conversion ── */
    path(fx, sizeof(fx), "unconverted");
    if (copy_file(g_bin, fx) != 0) {
        expect(0, "复制未转换夹具成功", "");
    } else {
        snprintf(args, sizeof(args), "-v \"%s\"", fx);
        printf("── paxctl -v <未转换的 ELF>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 1, "未转换 ELF 的 -v 退出码 (期望 1)", "");
        expect(strstr(buf, "does not have a PT_PAX_FLAGS program header") != NULL,
               "提示缺少 PT_PAX_FLAGS 程序头", "");
        expect(strstr(buf, "try conversion") != NULL, "提示 try conversion", "");
    }

    /* ── 4. 转换：-c 在带 PT_GNU_STACK 的 ELF 上 ── */
    path(fx, sizeof(fx), "toconvert");
    if (copy_file(g_bin, fx) != 0) {
        expect(0, "复制待转换夹具成功", "");
    } else {
        snprintf(args, sizeof(args), "-c \"%s\"", fx);
        printf("── paxctl -c <带 PT_GNU_STACK 的 ELF>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "-c 退出码 (期望 0)", "");
        expect(strstr(buf, "had a PT_GNU_STACK program header, converted") != NULL,
               "-c 报 had a PT_GNU_STACK program header, converted", "");

        snprintf(args, sizeof(args), "-c \"%s\"", fx);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "二次 -c 退出码 (期望 0)", "");
        expect(strstr(buf, "converted") == NULL,
               "二次 -c 不再报 converted（已转换，幂等）", "");

        snprintf(args, sizeof(args), "-v \"%s\"", fx);
        rc = run_capture(args, buf, sizeof(buf));
        expect(strstr(buf, "does not have a PT_PAX_FLAGS") == NULL,
               "转换后 -v 不再提示缺少程序头", "");
    }

    /* ── 5. 基准标志串 ── */
    if (reset_fixture() != 0) {
        expect(0, "复位夹具成功", "copy/-c/-z 失败");
        goto summary;
    }
    printf("── 基准（-c + -z 复位后）\n");
    if (!read_flags(flags, sizeof(flags))) {
        expect(0, "读取基准标志串", "");
    } else {
        snprintf(label, sizeof(label), "基准标志串 (期望 \"%s\")", g_base_flags);
        snprintf(d, sizeof(d), "实际 \"%s\"", flags);
        expect(strcmp(flags, g_base_flags) == 0, label,
               strcmp(flags, g_base_flags) == 0 ? "" : d);
    }

    /* ── 6. 逐标志：每个都从复位状态开始，断言精确标志串 ── */
    for (i = 0; i < (int)(sizeof(PER_FLAG) / sizeof(PER_FLAG[0])); i++) {
        char tag[64];
        if (reset_fixture() != 0) {
            expect(0, "复位夹具成功（逐标志用例）", "");
            break;
        }
        printf("── paxctl %s <fixture>\n", PER_FLAG[i][0]);
        snprintf(tag, sizeof(tag), "paxctl %s", PER_FLAG[i][0]);
        case_flags(tag, PER_FLAG[i][0], 0, PER_FLAG[i][1]);
    }

    /* ── 7. 组合标志 ── */
    if (reset_fixture() == 0) {
        printf("── paxctl -p -e -m -r -s <fixture>\n");
        case_flags("组合 -p -e -m -r -s", "-p -e -m -r -s", 0, "-p-s-m-x-e-r");
    }
    if (reset_fixture() == 0) {
        printf("── paxctl -P -E -M -R -S <fixture>\n");
        case_flags("组合 -P -E -M -R -S", "-P -E -M -R -S", 0, "P-S-M--xE-R-");
    }

    /* ── 8. 属性：-z 必然回到基准，且与之前状态无关 ── */
    {
        static const char *prior[] = { "-p -e -m -r -s", "-P -E -M -R -S",
                                       "-m -r -x" };
        for (i = 0; i < 3; i++) {
            if (reset_fixture() != 0) {
                expect(0, "复位夹具成功（-z 属性用例）", "");
                break;
            }
            path(fx, sizeof(fx), "fixture");
            snprintf(args, sizeof(args), "%s \"%s\"", prior[i], fx);
            if (run_capture(args, buf, sizeof(buf)) < 0) {
                expect(0, "-z 前置状态设置失败", "");
                break;
            }
            snprintf(args, sizeof(args), "-z \"%s\"", fx);
            if (run_capture(args, buf, sizeof(buf)) < 0) {
                expect(0, "-z 调用失败", "");
                break;
            }
            snprintf(label, sizeof(label), "-z 从 \"%s\" 复位回基准串", prior[i]);
            if (!read_flags(flags, sizeof(flags))) {
                expect(0, label, "读取标志串失败");
            } else {
                expect(strcmp(flags, g_base_flags) == 0, label,
                       strcmp(flags, g_base_flags) == 0 ? "" : flags);
            }
        }
    }

    /* ── 9. 夹具完整性：多轮改写后仍是可被 paxctl 解析的 ELF ── */
    printf("── 夹具完整性\n");
    if (reset_fixture() == 0) {
        path(fx, sizeof(fx), "fixture");
        snprintf(args, sizeof(args), "-p -e -m -r -s \"%s\"", fx);
        run_capture(args, buf, sizeof(buf));
        snprintf(args, sizeof(args), "-v \"%s\"", fx);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "多轮改写后 -v 仍成功 (期望 0)", "");
        expect(strstr(buf, "not a valid ELF") == NULL,
               "多轮改写后夹具仍是合法 ELF", "");
    }

summary:
    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
