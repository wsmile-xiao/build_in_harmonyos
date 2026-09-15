/* test_package/test_dasm.c — dasm 消费者测试
 *
 * 消费包内产物，并对**真实执行**做上游回归比对：
 *   T1  bin/dasm 存在且可执行
 *   T2  bin/dasm 为 ELF64 / AArch64
 *   T3  bin/ftohex 存在、可执行、为 ELF64 / AArch64
 *   T4  无参调用打印用法横幅（含 "DASM 2.20.14.1" 与 "Usage: dasm sourcefile"），
 *       且退出码 == ERROR_COMMAND_LINE(1) —— 用法路径不得报成功
 *   T5  share/dasm/machines/atari2600/vcs.h 已安装（用户经 -I 引入的机器头）
 *   T6  share/man/man1/dasm.1 已安装
 *   T7~T18  12 个上游回归用例：把上游用例的 .asm 原样写入临时文件，
 *       按上游 run_tests.sh 的同一命令汇编，产物与上游同名 .bin.ref 逐字节比对
 *   T19 ftohex 把 T7 产物转 Intel HEX，须以 ':' 开头、以 EOF 记录 ":00000001FF" 结尾
 *
 * 判据加固（沿用本仓已合入产线的 P2/P3 结论）：
 *   - popen 经 /bin/sh 中转：被信号杀死的子进程由 shell 转成 128+signum
 *     （SIGSEGV→139、SIGABRT→134）**正常退出**，WIFEXITED 恒为真 ——
 *     故判据把 126/127/>=128 一并视为"没跑起来"。
 *   - 循环读到 EOF 后才 pclose，避免输出超缓冲时的 SIGPIPE 假通过 / 死锁。
 *   - 不写 /tmp（OHOS 上 /tmp 只读）；一律写当前工作目录（conan 构建目录，可写）。
 *
 * 用法: test_dasm <package_folder>
 */
/* ★ 特性测试宏必须在所有 #include 之前。
 *
 * popen / pclose / access / WIFEXITED 都是 POSIX 而非 ISO C。在严格 ISO C 方言
 * （-std=c99/-std=c11，未定义 _POSIX_C_SOURCE）下，glibc 与 musl 都会**隐藏**
 * popen/pclose 的声明；缺声明时编译器按隐式 int 处理，`FILE *fp = popen(...)`
 * 会把 int 截断成指针 —— 编译只有 warning，运行直接 SIGSEGV。
 * 实测：不加此宏时本测试在 WSL/glibc 2.35 上崩溃（exit 139）。
 */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include "test_cases.h"

static int passed = 0, failed = 0;

static void expect(int cond, const char *name, const char *detail) {
    if (cond) { printf("PASS %s\n", name); passed++; }
    else { printf("FAIL %s %s\n", name, detail ? detail : ""); failed++; }
}

static int check_elf(const char *path, char *d, size_t n) {
    FILE *fp = fopen(path, "rb");
    if (!fp) { snprintf(d, n, "(unreadable)"); return 0; }
    unsigned char h[20];
    size_t got = fread(h, 1, sizeof(h), fp);
    fclose(fp);
    if (got < 20 || h[0] != 0x7f || h[1] != 'E' || h[2] != 'L' || h[3] != 'F') {
        snprintf(d, n, "(not ELF)");
        return 0;
    }
    unsigned int machine = (unsigned int)h[18] | ((unsigned int)h[19] << 8);
    if (h[4] != 2 || machine != 0xB7) {
        snprintf(d, n, "(elfclass=%u machine=0x%X want 2/0xB7)", h[4], machine);
        return 0;
    }
    snprintf(d, n, "(ELF64/AArch64)");
    return 1;
}

static int safe_run(const char *path, const char *args, char *out, size_t outlen,
                    int *code, int *killed) {
    char cmd[1400];
    if (args && *args)
        snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", path, args);
    else
        snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");
    if (!fp) { *code = -1; *killed = 0; return -1; }
    size_t n = 0, got;
    while (n < outlen - 1 && (got = fread(out + n, 1, outlen - 1 - n, fp)) > 0)
        n += got;
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);
    *code = *killed ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    if (*code == 126 || *code == 127 || *code >= 128) return -4;
    return 0;
}

/* 把内嵌用例写成 <name>.asm，返回 0 成功 */
static int write_case(const char *name, const char *src) {
    char fn[256];
    snprintf(fn, sizeof(fn), "%s.asm", name);
    FILE *fp = fopen(fn, "wb");
    if (!fp) return -1;
    fwrite(src, 1, strlen(src), fp);
    fclose(fp);
    return 0;
}

/* 读 <name>.bin，校验 2 字节 origin 头 + 正文与期望完全一致 */
static int compare_case_bin(const char *name, const unsigned char *exp,
                            unsigned int explen, unsigned int origin,
                            char *detail, size_t dlen) {
    char fn[256];
    snprintf(fn, sizeof(fn), "%s.bin", name);
    FILE *fp = fopen(fn, "rb");
    if (!fp) { snprintf(detail, dlen, "(%s missing)", fn); return 0; }
    unsigned char buf[8192];
    size_t got = fread(buf, 1, sizeof(buf), fp);
    fclose(fp);
    if (got != (size_t)explen + 2) {
        snprintf(detail, dlen, "(%s size=%u want %u+2)", fn, (unsigned int)got, explen);
        return 0;
    }
    unsigned int gotorigin = (unsigned int)buf[0] | ((unsigned int)buf[1] << 8);
    if (gotorigin != origin) {
        snprintf(detail, dlen, "(origin=0x%04X want 0x%04X)", gotorigin, origin);
        return 0;
    }
    if (memcmp(buf + 2, exp, explen) != 0) {
        unsigned int i, first = explen;
        for (i = 0; i < explen; i++)
            if (buf[2 + i] != exp[i]) { first = i; break; }
        snprintf(detail, dlen, "(byte %u: got 0x%02X want 0x%02X)",
                 first, buf[2 + first], exp[first]);
        return 0;
    }
    snprintf(detail, dlen, "(%u bytes exact)", explen + 2);
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_dasm: missing <package_folder> argument\n");
        return 2;
    }
    const char *pkg = argv[1];
    char path[1200], out[4096], ed[96], detail[512];
    int code, killed, r;
    size_t i;

    /* ---- T1/T2: dasm 二进制 ---- */
    snprintf(path, sizeof(path), "%s/bin/dasm", pkg);
    expect(access(path, F_OK) == 0, "T1 bin/dasm present", "(missing)");
    expect(access(path, X_OK) == 0, "T1 bin/dasm executable", "(no +x)");
    expect(check_elf(path, ed, sizeof(ed)), "T2 dasm is ELF64/AArch64", ed);

    /* ---- T3: ftohex 二进制 ---- */
    char ftohex[1200];
    snprintf(ftohex, sizeof(ftohex), "%s/bin/ftohex", pkg);
    expect(access(ftohex, F_OK) == 0, "T3 bin/ftohex present", "(missing)");
    expect(access(ftohex, X_OK) == 0, "T3 bin/ftohex executable", "(no +x)");
    expect(check_elf(ftohex, ed, sizeof(ed)), "T3 ftohex is ELF64/AArch64", ed);

    /* ---- T4: 无参用法横幅 + 退出码 ---- */
    code = 0; killed = 0;
    r = safe_run(path, "", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.120s)", r, killed, code, out);
    expect(r == 0, "T4 dasm no-arg runs (not killed / not 126-127-128+)", detail);
    expect(strstr(out, "Usage: dasm sourcefile") != NULL,
           "T4 prints usage", detail);
    expect(strstr(out, "DASM 2.20.14.1") != NULL,
           "T4 prints version banner DASM 2.20.14.1", detail);
    expect(code == 1,
           "T4 no-arg exit code == ERROR_COMMAND_LINE(1)", detail);

    /* ---- T5/T6: 随包资源（用独立缓冲，path 必须始终指向 dasm 二进制） ---- */
    {
        char res[1200];
        snprintf(res, sizeof(res), "%s/share/dasm/machines/atari2600/vcs.h", pkg);
        expect(access(res, F_OK) == 0, "T5 machines/atari2600/vcs.h installed", "(missing)");
        snprintf(res, sizeof(res), "%s/share/man/man1/dasm.1", pkg);
        expect(access(res, F_OK) == 0, "T6 man page dasm.1 installed", "(missing)");
    }

    /* ---- T7~T18: 上游回归用例逐字节比对 ---- */
    {
        FILE *probe = fopen("dasm_tp_cwd_probe.tmp", "wb");
        if (probe) { fclose(probe); remove("dasm_tp_cwd_probe.tmp"); }
        else {
            printf("FAIL T7 working directory not writable (cannot stage .asm)\n");
            failed++;
        }
    }

    for (i = 0; i < DASM_CASES_COUNT; i++) {
        const dasm_case_t *c = &DASM_CASES[i];
        char name[96];
        snprintf(name, sizeof(name), "T%zu %s upstream regression", (size_t)(7 + i), c->name);

        if (write_case(c->name, c->asm_src) != 0) {
            expect(0, name, "(cannot write .asm)");
            continue;
        }

        /* 复刻上游 test/run_tests.sh 的命令 */
        char args[512];
        snprintf(args, sizeof(args), "%s.asm -f1 -o%s.bin -L%s.list.txt -DINEEPROM",
                 c->name, c->name, c->name);
        code = 0; killed = 0;
        r = safe_run(path, args, out, sizeof(out), &code, &killed);

        char cmpdetail[300];
        int ok_size = compare_case_bin(c->name, c->expect, c->expect_len,
                                       c->origin, cmpdetail, sizeof(cmpdetail));
        snprintf(detail, sizeof(detail),
                 "(r=%d killed=%d rc=%d cmp=%s out=%.80s)", r, killed, code, cmpdetail, out);

        expect(r == 0 && code == 0, name, detail);
        expect(ok_size, name, detail);
    }

    /* ---- T19: ftohex 往返 ---- */
    {
        const dasm_case_t *c = &DASM_CASES[0];
        char args[512], hexname[128];
        snprintf(args, sizeof(args), "1 %s.bin %s.hex", c->name, c->name);
        code = 0; killed = 0;
        r = safe_run(ftohex, args, out, sizeof(out), &code, &killed);
        snprintf(hexname, sizeof(hexname), "%s.hex", c->name);
        snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.80s)", r, killed, code, out);
        expect(r == 0 && code == 0, "T19 ftohex runs on dasm output", detail);

        FILE *fp = fopen(hexname, "rb");
        if (!fp) {
            expect(0, "T19 ftohex produced Intel HEX", "(no .hex file)");
        } else {
            char hexbuf[512];
            size_t got = fread(hexbuf, 1, sizeof(hexbuf) - 1, fp);
            fclose(fp);
            hexbuf[got] = '\0';
            int starts = got > 0 && hexbuf[0] == ':';
            int ends = strstr(hexbuf, ":00000001FF") != NULL;
            snprintf(detail, sizeof(detail), "(first='%.20s' eof=%d)", hexbuf, ends);
            expect(starts && ends, "T19 ftohex produced Intel HEX", detail);
        }
    }

    printf("test dasm 2.20.15-202011092.20.14.1: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
