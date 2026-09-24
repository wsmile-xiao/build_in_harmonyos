/* test_msdl.c — msdl/1.2.7-r2 test_package（L1 + HarmonyOS 专项测试）
 *
 * 测试 1（基础可运行性）: 运行包内 msdl 二进制（无参数），验证打印
 *   usage 且退出码 1（预期错误路径，证明程序可执行、动态链接正常）。
 *
 * 测试 2（HarmonyOS 专项·ELF/动态依赖）: 直接解析包内 msdl 的 ELF —
 *   a) ELF64 / LSB / EM_AARCH64;
 *   b) PT_INTERP == /lib/ld-musl-aarch64.so.1（musl，OHOS 目标环境）;
 *   c) PT_DYNAMIC 的 DT_NEEDED 仅 libc.so（上游纯 libc，零外部依赖）。
 *   全部在进程内解析（不依赖 readelf 等 host 工具，CI 环境自包含）。
 *
 * 测试 3（HarmonyOS 专项·真实网络行为）: 进程内起极简 HTTP 服务器
 *   （socket/bind(127.0.0.1:0)/listen，fork 服务循环），msdl 真实发起
 *   HTTP 连接下载 64 KiB 文件，逐字节比对内容（socket/GET/解析响应/
 *   写盘全链路；msdl 先探测 mmsh 再 fallback http 的真实行为也被覆盖）。
 *
 * 任一测试失败则以非零退出码终止（conan create 视为 test 失败）。
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

#define DATA_SIZE 65536
static int g_failures = 0;

/* ---------- 小工具 ---------- */

static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint64_t le64(const uint8_t *p) {
    return (uint64_t)le32(p) | ((uint64_t)le32(p + 4) << 32);
}

static int write_all(int fd, const void *buf, size_t len)
{
    const char *p = (const char *)buf;
    while (len > 0) {
        ssize_t n = write(fd, p, len);
        if (n < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        p += n;
        len -= (size_t)n;
    }
    return 0;
}

/* 运行外部命令，捕获合并的 stdout+stderr（out 可为 NULL），返回退出码;
 * 启动失败返回 -1。 */
static int run_cmd(const char *path, char *const argv[], char *out, size_t out_sz)
{
    int fds[2];
    if (pipe(fds) < 0)
        return -1;
    posix_spawn_file_actions_t fa;
    posix_spawn_file_actions_init(&fa);
    posix_spawn_file_actions_adddup2(&fa, fds[1], STDOUT_FILENO);
    posix_spawn_file_actions_adddup2(&fa, fds[1], STDERR_FILENO);
    pid_t pid;
    int rc = posix_spawn(&pid, path, &fa, NULL, argv, environ);
    posix_spawn_file_actions_destroy(&fa);
    close(fds[1]);
    if (rc != 0) {
        close(fds[0]);
        return -1;
    }
    size_t total = 0;
    if (out && out_sz > 1) {
        ssize_t n;
        while (total < out_sz - 1 &&
               (n = read(fds[0], out + total, out_sz - 1 - total)) > 0)
            total += (size_t)n;
        out[total] = '\0';
    } else {
        char sink[4096];
        ssize_t n;
        while ((n = read(fds[0], sink, sizeof(sink))) > 0)
            ;
    }
    close(fds[0]);
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return -1;
}

/* ---------- 测试 2: ELF 解析 ---------- */

#define EM_AARCH64 183
#define PT_LOAD    1
#define PT_DYNAMIC 2
#define PT_INTERP  3
#define DT_NEEDED  1
#define DT_STRTAB  5

static int check_elf(const char *path)
{
    int failed = 0;
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        printf("FAIL: open %s: %s\n", path, strerror(errno));
        return 1;
    }
    uint8_t ehdr[64];
    if (pread(fd, ehdr, sizeof(ehdr), 0) != (ssize_t)sizeof(ehdr)) {
        printf("FAIL: read ELF header (too short)\n");
        close(fd);
        return 1;
    }
    if (memcmp(ehdr, "\x7f" "ELF", 4) != 0) {
        printf("FAIL: not an ELF file\n");
        close(fd);
        return 1;
    }
    if (ehdr[4] != 2 /* ELFCLASS64 */) {
        printf("FAIL: not ELF64 (class=%d)\n", ehdr[4]);
        failed = 1;
    }
    if (ehdr[5] != 1 /* ELFDATA2LSB */) {
        printf("FAIL: not little-endian\n");
        failed = 1;
    }
    uint16_t e_machine = le16(ehdr + 18);
    if (e_machine != EM_AARCH64) {
        printf("FAIL: e_machine=%u, expected EM_AARCH64(%d)\n", e_machine, EM_AARCH64);
        failed = 1;
    }
    uint64_t e_phoff = le64(ehdr + 32);
    uint16_t e_phentsize = le16(ehdr + 54);
    uint16_t e_phnum = le16(ehdr + 56);
    if (e_phnum == 0 || e_phentsize < 56) {
        printf("FAIL: no program headers\n");
        close(fd);
        return 1;
    }

    uint64_t interp_off = 0, interp_sz = 0;
    uint64_t dyn_off = 0, dyn_sz = 0;
    uint64_t load_vaddr[16], load_off[16], load_filesz[16];
    int nload = 0;
    for (int i = 0; i < e_phnum; i++) {
        uint8_t ph[64];
        if (e_phentsize > sizeof(ph)) e_phentsize = sizeof(ph);
        if (pread(fd, ph, e_phentsize, e_phoff + (uint64_t)i * e_phentsize) != e_phentsize)
            break;
        uint32_t p_type = le32(ph);
        if (p_type == PT_INTERP) {
            interp_off = le64(ph + 8);
            interp_sz = le64(ph + 32);
        } else if (p_type == PT_DYNAMIC) {
            dyn_off = le64(ph + 8);
            dyn_sz = le64(ph + 32);
        } else if (p_type == PT_LOAD && nload < 16) {
            load_off[nload] = le64(ph + 8);
            load_vaddr[nload] = le64(ph + 16);
            load_filesz[nload] = le64(ph + 32);
            nload++;
        }
    }

    char interp[256] = {0};
    if (interp_sz == 0 || interp_sz >= sizeof(interp)) {
        printf("FAIL: no PT_INTERP\n");
        close(fd);
        return 1;
    }
    if (pread(fd, interp, interp_sz, interp_off) != (ssize_t)interp_sz)
        interp[0] = '\0';
    else
        interp[interp_sz] = '\0';
    if (strstr(interp, "ld-musl-aarch64.so.1") == NULL) {
        printf("FAIL: interpreter is '%s', expected /lib/ld-musl-aarch64.so.1\n", interp);
        failed = 1;
    }

    if (dyn_off == 0 || dyn_sz < 16) {
        printf("FAIL: no PT_DYNAMIC\n");
        close(fd);
        return 1;
    }
    uint64_t strtab_vaddr = 0;
    int strtab_found = 0;
    uint64_t needed_off[32];
    int nneeded = 0;
    for (uint64_t o = 0; o + 16 <= dyn_sz; o += 16) {
        uint8_t d[16];
        if (pread(fd, d, 16, dyn_off + o) != 16)
            break;
        uint64_t tag = le64(d);
        if (tag == 0) /* DT_NULL */
            break;
        if (tag == DT_STRTAB) {
            strtab_vaddr = le64(d + 8);
            strtab_found = 1;
        } else if (tag == DT_NEEDED && nneeded < 32) {
            needed_off[nneeded++] = le64(d + 8);
        }
    }
    if (!strtab_found) {
        printf("FAIL: no DT_STRTAB\n");
        close(fd);
        return 1;
    }
    uint64_t strtab_off = 0;
    int mapped = 0;
    for (int i = 0; i < nload; i++) {
        if (load_vaddr[i] <= strtab_vaddr && strtab_vaddr < load_vaddr[i] + load_filesz[i]) {
            strtab_off = load_off[i] + (strtab_vaddr - load_vaddr[i]);
            mapped = 1;
            break;
        }
    }
    if (!mapped) {
        printf("FAIL: DT_STRTAB vaddr not backed by any PT_LOAD\n");
        close(fd);
        return 1;
    }
    int has_libc = 0;
    for (int i = 0; i < nneeded; i++) {
        char name[128] = {0};
        if (pread(fd, name, sizeof(name) - 1, strtab_off + needed_off[i]) <= 0)
            continue;
        if (strcmp(name, "libc.so") == 0) {
            has_libc = 1;
        } else {
            printf("FAIL: unexpected DT_NEEDED '%s' (expected only libc.so)\n", name);
            failed = 1;
        }
    }
    if (!has_libc) {
        printf("FAIL: libc.so not found in DT_NEEDED\n");
        failed = 1;
    }
    close(fd);
    return failed ? 1 : 0;
}

/* ---------- 测试 3: 进程内 HTTP 服务器 + 真实下载 ---------- */

static void serve_loop(int lfd, const char *data_path)
{
    static unsigned char data[DATA_SIZE];
    int dfd = open(data_path, O_RDONLY);
    if (dfd < 0)
        _exit(1);
    size_t got = 0;
    while (got < DATA_SIZE) {
        ssize_t n = read(dfd, data + got, DATA_SIZE - got);
        if (n <= 0)
            break;
        got += (size_t)n;
    }
    close(dfd);
    if (got != DATA_SIZE)
        _exit(1);

    for (;;) {
        int c = accept(lfd, NULL, NULL);
        if (c < 0) {
            if (errno == EINTR)
                continue;
            _exit(0);
        }
        /* 读掉请求头（到 \r\n\r\n 或 EOF），无论 GET 还是 mmsh 探测 */
        char req[8192];
        size_t used = 0;
        while (used < sizeof(req)) {
            ssize_t n = read(c, req + used, sizeof(req) - used);
            if (n <= 0)
                break;
            used += (size_t)n;
            if (memmem(req, used, "\r\n\r\n", 4))
                break;
        }
        char head[256];
        int hl = snprintf(head, sizeof(head),
                          "HTTP/1.1 200 OK\r\n"
                          "Content-Length: %d\r\n"
                          "Content-Type: application/octet-stream\r\n"
                          "Connection: close\r\n\r\n", DATA_SIZE);
        if (write_all(c, head, (size_t)hl) == 0)
            write_all(c, data, DATA_SIZE);
        close(c);
    }
}

static pid_t start_http_server(uint16_t *port, const char *data_path)
{
    int lfd = socket(AF_INET, SOCK_STREAM, 0);
    if (lfd < 0)
        return -1;
    int one = 1;
    setsockopt(lfd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0; /* 内核自动分配空闲端口 */
    if (bind(lfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(lfd);
        return -1;
    }
    if (listen(lfd, 8) < 0) {
        close(lfd);
        return -1;
    }
    struct sockaddr_in actual;
    socklen_t alen = sizeof(actual);
    if (getsockname(lfd, (struct sockaddr *)&actual, &alen) < 0) {
        close(lfd);
        return -1;
    }
    *port = ntohs(actual.sin_port);

    pid_t pid = fork();
    if (pid < 0) {
        close(lfd);
        return -1;
    }
    if (pid == 0) {
        signal(SIGPIPE, SIG_IGN);
        serve_loop(lfd, data_path);
        _exit(0);
    }
    close(lfd); /* 父进程不再需要；子进程已持有 */
    return pid;
}

static int files_identical(const char *a, const char *b)
{
    int fa = open(a, O_RDONLY), fb = open(b, O_RDONLY);
    if (fa < 0 || fb < 0) {
        if (fa >= 0) close(fa);
        if (fb >= 0) close(fb);
        return -1;
    }
    static char ba[DATA_SIZE], bb[DATA_SIZE];
    ssize_t na = read(fa, ba, DATA_SIZE), nb = read(fb, bb, DATA_SIZE);
    close(fa);
    close(fb);
    if (na < 0 || nb < 0)
        return -1;
    if (na != nb || memcmp(ba, bb, (size_t)na) != 0)
        return 1;
    return 0;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <msdl-binary>\n", argv[0]);
        return 2;
    }
    const char *msdl_bin = argv[1];
    char out[65536];

    /* 防 msdl 或服务器异常导致的无限挂起（真挂起即为测试失败） */
    alarm(120);

    /* ---------- 测试 1: 无参运行 usage + 退出码 1 ---------- */
    {
        char *const av[] = {(char *)msdl_bin, NULL};
        int rc = run_cmd(msdl_bin, av, out, sizeof(out));
        if (rc != 1) {
            printf("FAIL: no-args exit=%d (expected 1)\n", rc);
            g_failures++;
        } else if (!strstr(out, "Usage") || !strstr(out, "msdl")) {
            printf("FAIL: no-args output lacks usage:\n%s\n", out);
            g_failures++;
        } else {
            printf("PASS: no-args prints usage, exit=1\n");
        }
    }

    /* ---------- 测试 2: HarmonyOS 专项 ELF/动态依赖 ---------- */
    if (check_elf(msdl_bin) == 0)
        printf("PASS: ELF64 AArch64, musl interpreter, DT_NEEDED only libc.so\n");
    else
        g_failures++;

    /* ---------- 测试 3: 真实 HTTP 下载（本地服务器） ---------- */
    {
        char srv_dir[4200];
        if (getcwd(srv_dir, sizeof(srv_dir) - 32) == NULL) {
            printf("FAIL: getcwd: %s\n", strerror(errno));
            return 3;
        }
        strcat(srv_dir, "/msdl_srv_XXXXXX");
        if (mkdtemp(srv_dir) == NULL) {
            printf("FAIL: mkdtemp(%s): %s\n", srv_dir, strerror(errno));
            return 3;
        }
        char data_path[4400], out_path[4400];
        snprintf(data_path, sizeof(data_path), "%s/testdata.bin", srv_dir);
        snprintf(out_path, sizeof(out_path), "%s/downloaded.bin", srv_dir);

        /* 生成 64 KiB 确定性伪随机数据 */
        int fd = open(data_path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) {
            printf("FAIL: open %s: %s\n", data_path, strerror(errno));
            return 3;
        }
        for (int i = 0; i < DATA_SIZE; i += 4) {
            uint32_t v = (uint32_t)i * 2654435761u + 12345u;
            if (write_all(fd, &v, sizeof(v)) != 0) {
                printf("FAIL: write data: %s\n", strerror(errno));
                close(fd);
                return 3;
            }
        }
        close(fd);

        uint16_t port = 0;
        pid_t srv = start_http_server(&port, data_path);
        if (srv < 0) {
            printf("FAIL: start_http_server: %s\n", strerror(errno));
            return 3;
        }
        char url[128];
        snprintf(url, sizeof(url), "http://127.0.0.1:%u/testdata.bin", (unsigned)port);
        char *const av[] = {(char *)msdl_bin, (char *)"-v", (char *)"-o",
                            out_path, url, NULL};
        int rc = run_cmd(msdl_bin, av, out, sizeof(out));
        kill(srv, SIGKILL);
        waitpid(srv, NULL, 0);

        if (rc != 0) {
            printf("FAIL: msdl download exit=%d (expected 0)\n--- output ---\n%s\n", rc, out);
            g_failures++;
        } else {
            int cmp = files_identical(data_path, out_path);
            if (cmp == 0) {
                printf("PASS: real HTTP download of %d bytes, content identical\n", DATA_SIZE);
            } else {
                printf("FAIL: downloaded file differs from served data (cmp=%d)\n", cmp);
                g_failures++;
            }
        }
        unlink(out_path);
        unlink(data_path);
        rmdir(srv_dir);
    }

    if (g_failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d FAILURE(S)\n", g_failures);
    return 1;
}
