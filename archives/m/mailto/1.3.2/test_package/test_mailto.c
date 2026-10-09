/* test_mailto.c — mailto 1.3.2 消费者用例（共 17 条断言，5 组）
 *
 * mailto 是 CGI 可执行程序，没有可链接的库 API，因此本用例按"CGI 程序的
 * 真实调用方式"验证它：以子进程方式执行包内 bin/mailto，并对它的输出做
 * 确定性断言。断言文本全部取自 qemu-aarch64 + OHOS sysroot 下的**实测输出**
 * （早期版本误按源码里的 C 注释写了 "Version 1.3.2"，真机跑出来其实是
 * "mailto v1.3.2" —— 那段 "** Version 1.3.2 - 2.3.1999" 是注释，不打印）。
 * 全部用例不依赖网络、不依赖 sendmail。
 *
 * 用例覆盖（5 组 / 17 条断言）：
 *   1. 存在性：包内 bin/mailto 存在                      （1 条）
 *   2. -v 版本横幅：含 "mailto v1.3.2" 与 "Andreas Ley" （4 条）
 *   3. -h 用法：含 "Usage:" 与 "[-h] [-v]"                （4 条）
 *   4. 裸调用：输出完整 CGI 响应，含 "Content-type: text/html"
 *               与 "WWW Mail Gateway"                     （4 条）
 *   5. 非法选项 -Z：含 "unrecognized option" 且回显 Usage （4 条）
 *
 * 移植性说明：
 *   - 用 expect() 计数而非 assert()，保证全部用例都跑到并汇总结果
 *   - 不使用 /tmp：OHOS 的 /tmp 是只读挂载，临时文件建在 argv[1] 指向的
 *     包目录下，并在开跑前显式探测可写性
 *   - popen 捕获到内存里分析，循环读到 EOF 后再 pclose，避免僵尸管道
 *   - 返回码为 -1、被信号杀死、或 >=128（含 126/127）一律判为失败
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int g_checks = 0;
static int g_failures = 0;

static void expect(int cond, const char *what)
{
    ++g_checks;
    if (cond) {
        printf("  [PASS] %s\n", what);
    } else {
        ++g_failures;
        printf("  [FAIL] %s\n", what);
    }
}

/* 以内存方式捕获子进程 stdout+stderr。调用者需用 free() 释放。 */
static char *capture(const char *exe, const char *arg, int *exit_code)
{
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "'%s' %s 2>&1", exe, arg);

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        *exit_code = -1;
        return NULL;
    }

    size_t cap = 4096, len = 0;
    char *buf = (char *)malloc(cap);
    if (buf == NULL) {
        pclose(fp);
        *exit_code = -1;
        return NULL;
    }

    for (;;) {
        if (len + 1024 > cap) {
            size_t ncap = cap * 2;
            char *nbuf = (char *)realloc(buf, ncap);
            if (nbuf == NULL) {
                free(buf);
                pclose(fp);
                *exit_code = -1;
                return NULL;
            }
            buf = nbuf;
            cap = ncap;
        }
        size_t n = fread(buf + len, 1, 1024, fp);
        len += n;
        if (n == 0) {
            break; /* 到 EOF 才退出，避免管道阻塞 */
        }
    }
    buf[len < cap ? len : cap - 1] = '\0';

    int rc = pclose(fp);
    if (rc == -1) {
        *exit_code = -1;
    } else if (WIFSIGNALED(rc)) {
        *exit_code = 128 + WTERMSIG(rc);
    } else {
        *exit_code = WIFEXITED(rc) ? WEXITSTATUS(rc) : -1;
    }
    return buf;
}

static int ran_ok(int rc)
{
    /* 被信号杀死（含 128+N）与 shell 的 126/127 都视为失败 */
    return !(rc < 0 || rc == 126 || rc == 127 || rc >= 128);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <package_root>\n", argv[0]);
        return 2;
    }
    const char *root = argv[1];

    char exe[4096];
    snprintf(exe, sizeof(exe), "%s/bin/mailto", root);

    /* ---- 0. 探针文件建在包目录下，验证可写（OHOS 的 /tmp 只读） ---- */
    char probe[4096];
    snprintf(probe, sizeof(probe), "%s/.wtest", root);
    FILE *pf = fopen(probe, "w");
    if (pf != NULL) {
        fputs("ok", pf);
        fclose(pf);
        remove(probe);
    }

    printf("== mailto 1.3.2 消费者用例 ==\n");

    /* ---- 1. 存在性 ---- */
    struct stat st;
    int exists = (stat(exe, &st) == 0) && S_ISREG(st.st_mode);
    expect(exists, "包内存在 bin/mailto");
    if (!exists) {
        printf("  找不到: %s\n", exe);
        printf("== 合计 %d 项，失败 %d 项 ==\n", g_checks, g_failures);
        return 1;
    }

    /* ---- 2. -v 版本横幅 ---- */
    int rc = 0;
    char *out = capture(exe, "-v", &rc);
    expect(out != NULL, "-v 可被拉起执行");
    if (out != NULL) {
        expect(ran_ok(rc), "-v 未被信号杀死");
        /* 实测（qemu-aarch64 + OHOS sysroot）输出：
         *   mailto v1.3.2
         *   (c) 1994-1998 by Andreas Ley (Andreas.Ley@rz.uni-karlsruhe.de)
         */
        expect(strstr(out, "mailto v1.3.2") != NULL,
               "-v 输出包含 'mailto v1.3.2'");
        expect(strstr(out, "Andreas Ley") != NULL,
               "-v 输出包含作者署名 'Andreas Ley'");
        if (strstr(out, "mailto v1.3.2") == NULL) {
            printf("  ---- 输出前 400 字符 ----\n%s\n", out);
        }
        free(out);
    }

    /* ---- 3. -h 用法 ---- */
    out = capture(exe, "-h", &rc);
    expect(out != NULL, "-h 可被拉起执行");
    if (out != NULL) {
        expect(ran_ok(rc), "-h 未被信号杀死");
        /* 实测输出末行为：Usage: <argv0> [-h] [-v] */
        expect(strstr(out, "Usage:") != NULL, "-h 输出包含 'Usage:'");
        expect(strstr(out, "[-h] [-v]") != NULL, "-h 输出包含选项说明 '[-h] [-v]'");
        free(out);
    }

    /* ---- 4. 裸调用：以 CGI 身份输出一份完整的 WWW Mail Gateway HTML 表单 ----
     * 实测输出含 Content-type: text/html 与 <TITLE>WWW Mail Gateway</TITLE>，
     * 这是 mailto 的核心功能（CGI 表单网关），比只验证"能启动"强得多。
     * 注意：这里不设置任何 CGI 环境变量，程序走 QUERY_STRING 为空的默认分支，
     * 直接吐默认表单，不会调用 sendmail、不产生任何网络行为。
     */
    out = capture(exe, "", &rc);
    expect(out != NULL, "裸调用可被拉起执行");
    if (out != NULL) {
        expect(ran_ok(rc), "裸调用未被信号杀死");
        expect(strstr(out, "Content-type: text/html") != NULL,
               "裸调用输出 CGI 头 'Content-type: text/html'");
        expect(strstr(out, "WWW Mail Gateway") != NULL,
               "裸调用输出 '<TITLE>WWW Mail Gateway</TITLE>'");
        free(out);
    }

    /* ---- 5. 非法选项：应给出可读诊断并受控退出，而非崩溃 ---- */
    out = capture(exe, "-Z", &rc);
    expect(out != NULL, "非法选项可被拉起执行");
    if (out != NULL) {
        expect(ran_ok(rc), "非法选项未被信号杀死");
        expect(strstr(out, "unrecognized option") != NULL,
               "非法选项输出 'unrecognized option' 诊断");
        expect(strstr(out, "Usage:") != NULL,
               "非法选项仍给出 Usage 提示");
        free(out);
    }

    printf("== 合计 %d 项，失败 %d 项 ==\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
