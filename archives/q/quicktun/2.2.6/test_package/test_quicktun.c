/* QuickTun 2.2.6 —— 消费者测试（test_package）
 *
 * 视角：我是 quicktun 这个**应用包**的使用者。我能拿到的公开面就是它装进 bin/
 * 的可执行文件。本程序不 include 被测包的任何头（应用包没有头），而是：
 *   (1) 以绝对路径调用随包发布的 `quicktun.keypair`，把它当外部命令用；
 *   (2) 另用 **libsodium 自己**在进程内算出同一秘密标量对应的 Curve25519 公钥，
 *       作为独立预言机交叉核对被测二进制的输出。
 * 任何一条断言不过 → 非零退出码 → conan create 的 test 步骤失败。
 *
 * 为什么选 keypair：它是 QuickTun 里唯一**不需要 TUN 设备、不需要 root、
 * 不需要网络**就能跑到真实加密代码的路径（守护进程主路径要 /dev/net/tun，
 * 在构建环境里是被拒的，见 notes.md 的能力矩阵）。
 *
 * 注意一个诚实的边界：本文件的公钥比对**不能**区分后端是 libsodium 还是
 * 仓库自带的 TweetNaCl —— 实测两者对同一标量给出相同结果（同一 Curve25519
 * 原语）。后端归真是由配方 build() 里的链接期符号断言把住的，不在这里。
 */
#include <sodium.h>

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

#ifndef QUICKTUN_KEYPAIR
#define QUICKTUN_KEYPAIR "quicktun.keypair"
#endif
#ifndef QUICKTUN_VERSION
#define QUICKTUN_VERSION "2.2.6"
#endif

#define KEYBYTES 32
#define HEXKEY (KEYBYTES * 2)
#define CAP 4096

static int failures = 0;
static int checks = 0;

static void failf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "  [FAIL] ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
}

static void checkf(int ok, const char *fmt, ...)
{
    va_list ap;
    checks++;
    if (ok)
        return;
    fprintf(stderr, "  [FAIL] check #%d: ", checks);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
}

/* 运行外部命令，二进制安全地捕获 stdout+stderr 于 buf，返回打包值：
 *   低 8 位 = 退出码（信号终止时为 0x7f|sig，便于与正常码区分），
 *   其余    = 捕获字节数。
 * 说明：错误信息走 stderr，因此必须 2>&1 合并，否则下面的 D 组断言看不到
 * "Invalid secret key argument" 这类定向报错文本。 */
static long run_capture(const char *cmd, unsigned char *buf, size_t cap)
{
    FILE *p;
    size_t n = 0;
    int status;

    p = popen(cmd, "r");
    if (!p)
        return -1;
    while (n < cap) {
        size_t got = fread(buf + n, 1, cap - n, p);
        if (got == 0)
            break;
        n += got;
    }
    status = pclose(p);
    /* pclose 给的是 wait status，不是退出码：必须经 WEXITSTATUS 解码。
     * （直接 status & 0xff 会把 exit 255 读成 0 —— 那是本测试自己的夹具 bug） */
    if (WIFSIGNALED(status))
        return (long)(0x7f | WTERMSIG(status)) | ((long)n << 8);
    if (WIFEXITED(status))
        return (long)(WEXITSTATUS(status) & 0xff) | ((long)n << 8);
    return (long)0x7f | ((long)n << 8);
}

static int exit_of(long packed) { return (int)(packed & 0xff); }
static long len_of(long packed) { return packed >> 8; }

static void to_hex(const unsigned char *in, size_t n, char *out)
{
    for (size_t i = 0; i < n; i++)
        sprintf(out + i * 2, "%02x", in[i]);
    out[n * 2] = '\0';
}

/* 从输出里找出 "<64hex> <64hex>" 这一行（前面会有上游打印的 banner） */
static int find_keyline(const unsigned char *buf, size_t len, char *sk, char *pk)
{
    char text[CAP];
    char *line, *save = NULL;
    size_t n = len < sizeof(text) - 1 ? len : sizeof(text) - 1;

    memcpy(text, buf, n);
    text[n] = '\0';
    for (line = strtok_r(text, "\n", &save); line;
         line = strtok_r(NULL, "\n", &save)) {
        if (strlen(line) != HEXKEY * 2 + 1)
            continue;
        if (line[HEXKEY] != ' ')
            continue;
        memcpy(sk, line, HEXKEY);
        sk[HEXKEY] = '\0';
        memcpy(pk, line + HEXKEY + 1, HEXKEY);
        pk[HEXKEY] = '\0';
        if (strspn(sk, "0123456789abcdef") == HEXKEY &&
            strspn(pk, "0123456789abcdef") == HEXKEY)
            return 1;
    }
    return 0;
}

/* 二进制安全的子串查找：不用 memmem（那是 _GNU_SOURCE 才有的扩展，musl 上
 * 不开 feature 宏就没有它），自己写一个，避免依赖任何 feature-test 宏。 */
static int contains(const unsigned char *hay, size_t hlen, const char *needle)
{
    size_t nlen = strlen(needle);
    size_t i;

    if (nlen == 0 || hlen < nlen)
        return 0;
    for (i = 0; i + nlen <= hlen; i++) {
        if (hay[i] == needle[0] && memcmp(hay + i, needle, nlen) == 0)
            return 1;
    }
    return 0;
}

static void build_cmd(char *out, size_t cap, const char *extra)
{
    /* 必须 2>&1 合并：上游 errorexit() 把定向报错写到 **stderr**，
     * 若丢进 /dev/null 则 D 组"非法入参要给出指定错误信息"的断言永远看不到
     * 被测物真实说了什么 —— 那是本测试的采集缺陷，不是被测物的缺陷。 */
    snprintf(out, cap, "\"%s\" %s 2>&1", QUICKTUN_KEYPAIR, extra);
}

int main(void)
{
    unsigned char buf[CAP];
    char cmd[CAP * 2], sk_hex[HEXKEY + 1], pk_hex[HEXKEY + 1];
    char expect_pub[HEXKEY + 1], expect_line[HEXKEY * 2 + 8];
    unsigned char sk[KEYBYTES], oracle_pk[KEYBYTES], got_pk[KEYBYTES];
    long r;
    size_t n;

    printf("quicktun 2.2.6 消费者测试：调用随包 quicktun.keypair，并用 libsodium 独立核对\n");
    if (sodium_init() < 0) {
        fprintf(stderr, "[FATAL] libsodium sodium_init() 失败\n");
        return 1;
    }
    printf("  预言机 libsodium = %s\n", sodium_version_string());

    /* ---- A. 版本面：随包二进制自报版本必须与配方版本一致 ---- */
    build_cmd(cmd, sizeof(cmd), "-v");
    r = run_capture(cmd, buf, sizeof(buf));
    n = (size_t)len_of(r);
    checkf(exit_of(r) == 0, "A1 `quicktun.keypair -v` 退出码应为 0，实得 %d", exit_of(r));
    checkf(contains(buf, n, "QuickTun " QUICKTUN_VERSION),
           "A2 `-v` 输出应含 \"QuickTun %s\"（版本串不得归一化）", QUICKTUN_VERSION);

    /* ---- B. 四个固定标量：被测输出 vs libsodium 预言机 ---- */
    static const char *secrets[] = {
        "0100000000000000000000000000000000000000000000000000000000000000",
        "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        "77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a",
        "5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88a017",
    };
    for (size_t i = 0; i < sizeof(secrets) / sizeof(secrets[0]); i++) {
        const char *in = secrets[i];
        char arg[HEXKEY + 32];

        if (sodium_hex2bin(sk, sizeof(sk), in, strlen(in), NULL, NULL, NULL) != 0) {
            failf("B%zu 测试自身夹具坏：sodium_hex2bin 拒绝了我的常量", i);
            continue;
        }
        if (crypto_scalarmult_base(oracle_pk, sk) != 0) {
            failf("B%zu 预言机 crypto_scalarmult_base 失败", i);
            continue;
        }
        to_hex(oracle_pk, KEYBYTES, expect_pub);

        snprintf(arg, sizeof(arg), "-i %s -o space", in);
        build_cmd(cmd, sizeof(cmd), arg);
        r = run_capture(cmd, buf, sizeof(buf));
        n = (size_t)len_of(r);
        checkf(exit_of(r) == 0, "B%zu.1 rc 应为 0，实得 %d", i, exit_of(r));
        if (!find_keyline(buf, n, sk_hex, pk_hex)) {
            failf("B%zu.2 输出里找不到 \"<64hex> <64hex>\" 数据行", i);
            continue;
        }
        checkf(strcmp(sk_hex, in) == 0,
               "B%zu.3 回显的秘密标量应等于输入（得到 %s）", i, sk_hex);
        checkf(strcmp(pk_hex, expect_pub) == 0,
               "B%zu.4 公钥应与 libsodium 独立计算一致：期望 %s 实得 %s", i,
               expect_pub, pk_hex);
        if (sodium_hex2bin(got_pk, sizeof(got_pk), pk_hex, strlen(pk_hex),
                           NULL, NULL, NULL) != 0)
            failf("B%zu.5 被测输出的公钥不是合法 hex", i);

        /* 确定性：同输入两次必须完全一致 */
        {
            long r2 = run_capture(cmd, buf, sizeof(buf));
            char sk2[HEXKEY + 1], pk2[HEXKEY + 1];
            checkf(find_keyline(buf, (size_t)len_of(r2), sk2, pk2) &&
                   strcmp(pk2, pk_hex) == 0,
                   "B%zu.6 同输入复跑结果必须一致（确定性）", i);
        }

        /* human 模式：同一公钥，带 "PUBLIC: " 前缀 */
        {
            snprintf(arg, sizeof(arg), "-i %s", in);
            build_cmd(cmd, sizeof(cmd), arg);
            r = run_capture(cmd, buf, sizeof(buf));
            n = (size_t)len_of(r);
            snprintf(expect_line, sizeof(expect_line), "PUBLIC: %s", expect_pub);
            checkf(exit_of(r) == 0 && contains(buf, n, expect_line),
                   "B%zu.7 human 模式应含 \"%s\"", i, expect_line);
            snprintf(expect_line, sizeof(expect_line), "SECRET: %s", in);
            checkf(contains(buf, n, expect_line), "B%zu.8 human 模式应含 \"%s\"",
                   i, expect_line);
        }

        /* bin 模式：尾部 64 字节必须是 secret||public（banner 在前） */
        {
            snprintf(arg, sizeof(arg), "-i %s -o bin", in);
            build_cmd(cmd, sizeof(cmd), arg);
            r = run_capture(cmd, buf, sizeof(buf));
            n = (size_t)len_of(r);
            checkf(exit_of(r) == 0 && n >= 64, "B%zu.9 bin 模式应至少 64 字节，实得 %zu",
                   i, n);
            if (n >= 64) {
                to_hex(buf + n - 64, KEYBYTES, sk_hex);
                to_hex(buf + n - 32, KEYBYTES, pk_hex);
                checkf(strcmp(sk_hex, in) == 0, "B%zu.10 bin 前 32 字节应为秘密标量", i);
                checkf(strcmp(pk_hex, expect_pub) == 0, "B%zu.11 bin 后 32 字节应为预言机公钥", i);
            }
        }
    }

    /* ---- C. 随机密钥路径必须真的随机（无 -i）---- */
    {
        char a[HEXKEY * 2 + 2], b[HEXKEY * 2 + 2];
        build_cmd(cmd, sizeof(cmd), "-o space");
        r = run_capture(cmd, buf, sizeof(buf));
        checkf(exit_of(r) == 0 && find_keyline(buf, (size_t)len_of(r), a, a + HEXKEY + 1),
               "C1 随机模式首次调用应成功产出密钥行");
        build_cmd(cmd, sizeof(cmd), "-o space");
        r = run_capture(cmd, buf, sizeof(buf));
        checkf(exit_of(r) == 0 && find_keyline(buf, (size_t)len_of(r), b, b + HEXKEY + 1),
               "C2 随机模式第二次调用应成功");
        checkf(strcmp(a, b) != 0, "C3 两次随机密钥不应相同（随机源可用性）");
    }

    /* ---- D. 边界：非法输入必须被拒绝，且以 255 退出 ---- */
    {
        static const char *bad[] = {
            "-i 0102",                                                            /* 长度不足 */
            "-i zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz", /* 非 hex */
        };
        for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
            build_cmd(cmd, sizeof(cmd), bad[i]);
            r = run_capture(cmd, buf, sizeof(buf));
            checkf(exit_of(r) == 255, "D%zu.1 非法 -i 参数应以 255 退出，实得 %d",
                   i, exit_of(r));
            checkf(contains(buf, (size_t)len_of(r), "Invalid secret key argument"),
                   "D%zu.2 非法 -i 参数应报 Invalid secret key argument", i);
        }
        build_cmd(cmd, sizeof(cmd), "-o bogus -i 0100000000000000000000000000000000000000000000000000000000000000");
        r = run_capture(cmd, buf, sizeof(buf));
        checkf(exit_of(r) == 255 && contains(buf, (size_t)len_of(r),
                                             "Invalid argument specified for -o"),
               "D3 非法 -o 取值应被拒绝并给出定向错误信息");
    }

    printf("\n检查项 %d 条，失败 %d 条\n", checks, failures);
    if (failures) {
        printf("VERDICT: FAIL\n");
        return 1;
    }
    printf("VERDICT: PASS\n");
    return 0;
}
