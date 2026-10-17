/* test_package/test_dact.c — dact 0.8.42 消费者测试
 *
 * 消费包内产物：
 *   T1 bin/dact 存在且可执行
 *   T2 ELF64 / AArch64
 *   T3 `-h` 真实执行：未被信号杀死、未落在 126/127/128+，且输出含源码 usage 字面
 *      （dact.c: printf("usage: %s [options...] [file ...]\n", argv[0]) ）
 *   T4 运行时配置 etc/dact.conf 已安装（dact 启动即读取；上游由 Makefile 生成）
 *   T5 `-V` 真实执行：同样排除加载失败码（版本分支，dact.c 的 -V 选项）
 *
 * 判据加固（吸收 AI 检视 P2/P3）：
 *   - popen 经 /bin/sh 中转：被信号杀死的子进程由 shell 转成 128+signum
 *     （SIGSEGV→139、SIGABRT→134）**正常退出**，WIFEXITED 恒为真 ——
 *     故判据把 126/127/>=128 一并视为"没跑起来"。
 *   - 循环读干管道后才 pclose，避免输出超缓冲时的 SIGPIPE 假通过 / 死锁。
 *   - 不写 /tmp（OHOS 上 /tmp 只读）。
 *
 * 用法: test_dact <package_folder>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

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

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_dact: missing <package_folder> argument\n");
        return 2;
    }
    const char *pkg = argv[1];
    char path[1200], out[4096], ed[96], detail[260];
    int code, killed, r;

    snprintf(path, sizeof(path), "%s/bin/dact", pkg);
    expect(access(path, F_OK) == 0, "T1 dact present", "(missing)");
    expect(access(path, X_OK) == 0, "T1 dact executable", "(no +x)");
    expect(check_elf(path, ed, sizeof(ed)), "T2 dact is ELF64/AArch64", ed);

    code = 0; killed = 0;
    r = safe_run(path, "-h", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.110s)", r, killed, code, out);
    expect(r == 0, "T3 dact -h runs (not killed / not 126-127-128+)", detail);
    expect(strstr(out, "usage") != NULL, "T3 dact -h prints usage", detail);

    snprintf(path, sizeof(path), "%s/etc/dact.conf", pkg);
    expect(access(path, F_OK) == 0, "T4 dact.conf installed", "(missing)");

    snprintf(path, sizeof(path), "%s/bin/dact", pkg);
    code = 0; killed = 0;
    r = safe_run(path, "-V", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.110s)", r, killed, code, out);
    expect(r == 0, "T5 dact -V runs (not killed / not 126-127-128+)", detail);

    printf("test dact 0.8.42: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
