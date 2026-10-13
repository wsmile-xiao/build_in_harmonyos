/* test_shadowsocks_e2e.c — shadowsocks-libev 3.3.5 OHOS 消费者端到端测试
 *
 * 设计目标（对齐赛事 rule4 / rule12）：
 *   1) 真实执行上游功能，而不是只做断言：本用例自己实现一个最小 SOCKS5
 *      客户端 + 一个最小 HTTP 源站，在进程内起「源站 → ss-server →
 *      ss-local(SOCKS5) → 客户端」的完整回环，验证真实的加密隧道收发。
 *   2) 离线可复现：上游 tests/test.py 硬依赖公网
 *      （默认 http://www.google.com/ 与 8.8.8.8:53），在 CI 与真机上必然
 *      失败。本用例把「客户端、代理、源站」全部放在本机 loopback，
 *      不出网、不依赖 DNS、不需要 curl/dig/python。
 *   3) 覆盖多种加密套件，验证 AEAD 与流密码两条代码路径。
 *
 * 工作方式：本程序既是客户端也是被测进程的父进程。
 *   fork 出 ss-server 与 ss-local（路径由 argv[1] 传入，即被 Conan 打包的
 *   bin 目录），再自己作为 SOCKS5 客户端经 ss-local 访问内建 HTTP 源站。
 *   源站在本进程内用 fork 出的子进程提供（纯 socket、无第三方依赖）。
 *
 * 退出码 0 = 全部通过，非 0 = 有失败（并打印逐项结果）。
 */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define ORIGIN_PORT 18080
#define SRV_PORT    18388
#define LOC_PORT    11081
#define PASSWORD    "ohpc-test-password-123456"

static const char *ORIGIN_BODY = "OHPC_SHADOWSOCKS_E2E_PAYLOAD_0123456789";

static int g_pass = 0;
static int g_fail = 0;

static void report(const char *cipher, const char *what, int ok, const char *detail)
{
    printf("  [%s] %-34s %s%s%s\n", ok ? "PASS" : "FAIL", what,
           cipher ? cipher : "-", detail && *detail ? " " : "",
           detail ? detail : "");
    fflush(stdout);
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
    }
}

/* ---------- 内建 HTTP 源站（子进程） ---------- */
/* ready_fd >= 0 时，在 listen() 成功后写 1 字节 'R'；失败写 'E'。
 * 父进程据此判定就绪（P2-7），不再盲等 sleep(1)。 */
static int run_origin(int ready_fd)
{
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int one = 1;
    struct sockaddr_in a;
    if (ls < 0) {
        if (ready_fd >= 0) { (void)!write(ready_fd, "E", 1); }
        return 1;
    }
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(ORIGIN_PORT);
    if (bind(ls, (struct sockaddr *)&a, sizeof(a)) < 0 || listen(ls, 8) < 0) {
        if (ready_fd >= 0) { (void)!write(ready_fd, "E", 1); }
        return 1;
    }
    if (ready_fd >= 0) {
        (void)!write(ready_fd, "R", 1);
        close(ready_fd);            /* 就绪后立即关闭，避免泄漏到子进程后续逻辑 */
    }
    for (;;) {
        int c = accept(ls, NULL, NULL);
        char buf[1024];
        char resp[512];
        int n;
        if (c < 0) {
            if (errno == EINTR) {
                continue;           /* 被信号打断：立即重试 */
            }
            if (errno == EMFILE || errno == ENFILE || errno == ENOBUFS) {
                /* 资源耗尽：退避后重试，避免忙等烧 CPU 并刷屏 */
                struct timespec ts = { 0, 20 * 1000 * 1000 }; /* 20ms */
                nanosleep(&ts, NULL);
                continue;
            }
            continue;
        }
        n = (int)read(c, buf, sizeof(buf) - 1);
        (void)n;
        snprintf(resp, sizeof(resp),
                 "HTTP/1.1 200 OK\r\nContent-Length: %zu\r\n"
                 "Connection: close\r\n\r\n%s",
                 strlen(ORIGIN_BODY), ORIGIN_BODY);
        (void)write(c, resp, strlen(resp));
        close(c);
    }
    return 0;
}

/* ---------- 最小 SOCKS5 客户端 ---------- */
/* 返回 0 当且仅当隧道建立成功**且**收到非空、未截断的应用层数据；
 * -1 = 连接/握手/空响应失败，-2 = 响应超出 outsz 被截断。
 * 调用方必须要求 rc == 0，不能只依赖 strstr 兜底（见 P2-6）。 */
static int socks5_get(int port, const char *path, char *out, size_t outsz)
{
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a;
    unsigned char buf[512];
    unsigned char r[512];
    size_t need;
    int truncated;
    int n;

    if (s < 0) {
        return -1;
    }
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons((unsigned short)port);
    if (connect(s, (struct sockaddr *)&a, sizeof(a)) < 0) {
        close(s);
        return -1;
    }
    /* greeting: ver=5, nmethods=1, no-auth */
    buf[0] = 0x05; buf[1] = 0x01; buf[2] = 0x00;
    if (write(s, buf, 3) != 3) { close(s); return -1; }
    if (read(s, r, 2) != 2 || r[0] != 0x05 || r[1] != 0x00) { close(s); return -1; }

    /* CONNECT to 127.0.0.1:ORIGIN_PORT (ATYP=IPv4) */
    buf[0] = 0x05; buf[1] = 0x01; buf[2] = 0x00; buf[3] = 0x01;
    buf[4] = 127; buf[5] = 0; buf[6] = 0; buf[7] = 1;
    buf[8] = (unsigned char)(ORIGIN_PORT >> 8);
    buf[9] = (unsigned char)(ORIGIN_PORT & 0xff);
    if (write(s, buf, 10) != 10) { close(s); return -1; }
    /* reply: ver rep rsv atyp + addr(4) + port(2) = 10 bytes for IPv4 */
    if (read(s, r, 10) != 10) { close(s); return -1; }
    if (r[1] != 0x00) { close(s); return -1; }

    /* HTTP GET through the tunnel */
    n = snprintf((char *)buf, sizeof(buf),
                 "GET %s HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n",
                 path);
    if (write(s, buf, (size_t)n) != n) { close(s); return -1; }

    /* 契约（P2-6）：返回 0 当且仅当**确实收到了响应体**且未被截断。
     * 原实现在首字节 read()<=0 时 break 后仍 return 0，把空响应/被截断的
     * 响应当成功；调用方的 strstr 兜底只是碰巧遮住了这个契约破坏。 */
    need = 0;
    truncated = 0;
    for (;;) {
        ssize_t got = read(s, r, sizeof(r));
        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (got == 0) {
            break;                  /* 对端正常关闭 */
        }
        if (need + (size_t)got < outsz) {
            memcpy(out + need, r, (size_t)got);
            need += (size_t)got;
        } else {
            truncated = 1;          /* 缓冲写满：明确标记，不再静默丢弃 */
        }
    }
    out[need < outsz ? need : outsz - 1] = '\0';
    close(s);
    if (need == 0) {
        return -1;                  /* 空响应不是成功 */
    }
    if (truncated) {
        return -2;                  /* 截断：调用方需区分于"内容不匹配" */
    }
    return 0;
}

/* fork 失败时返回 -1。调用方必须检查返回值：绝不能把 -1 交给 kill()，
 * 因为 kill(-1, SIGTERM) 会向当前用户的所有进程广播 SIGTERM
 * （包括测试宿主 / CI 代理），属灾难性误伤。 */
static pid_t spawn(const char *bin, char *const argv[])
{
    pid_t p = fork();
    if (p == 0) {
        /* 静音被代理进程的 INFO 日志，保持测试输出可读。 */
        freopen("/dev/null", "w", stdout);
        freopen("/dev/null", "w", stderr);
        execv(bin, argv);
        _exit(127);
    }
    if (p < 0) {
        fprintf(stderr, "fork() failed for %s: %s\n", bin, strerror(errno));
    }
    return p;
}

/* 只对有效的（> 0）pid 发信号并回收，杜绝 kill(-1, ...) 广播。 */
static void reap(pid_t p)
{
    if (p > 0) {
        kill(p, SIGTERM);
        waitpid(p, NULL, 0);
    }
}

int main(int argc, char **argv)
{
    const char *bindir;
    char ss_server[1024], ss_local[1024];
    const char *ciphers[] = {
        "aes-256-gcm", "chacha20-ietf-poly1305",
        "aes-256-cfb", "rc4-md5"
    };
    size_t nciphers = sizeof(ciphers) / sizeof(ciphers[0]);
    size_t i;
    pid_t origin;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <bindir>\n", argv[0]);
        return 2;
    }
    bindir = argv[1];
    snprintf(ss_server, sizeof(ss_server), "%s/ss-server", bindir);
    snprintf(ss_local, sizeof(ss_local), "%s/ss-local", bindir);

    signal(SIGPIPE, SIG_IGN);

    /* 1) 启动内建源站（P2-7：用 pipe 做就绪握手，替代盲等 sleep(1)）
     * 原实现在 bind/listen 失败时子进程直接退出而父进程无感知，
     * 随后 4 个 cipher 全报 "payload NOT matched"，
     * 把"源站没起来"误判为"产品回归"。这里带超时读握手字节，
     * 失败即给出明确诊断并以独立退出码中止。 */
    {
        int rp[2];
        if (pipe(rp) != 0) {
            fprintf(stderr, "pipe() failed for origin readiness: %s\n",
                    strerror(errno));
            return 2;
        }
        origin = fork();
        if (origin == 0) {
            close(rp[0]);
            _exit(run_origin(rp[1]));
        }
        if (origin < 0) {
            fprintf(stderr, "fork() failed for origin server: %s\n",
                    strerror(errno));
            close(rp[0]); close(rp[1]);
            return 2;
        }
        close(rp[1]);
        {
            /* 最多等 5s 就绪；用 select 做超时，避免在 read 上永久阻塞 */
            fd_set rfds;
            struct timeval tv;
            char rb = 0;
            int sel;
            FD_ZERO(&rfds);
            FD_SET(rp[0], &rfds);
            tv.tv_sec = 5;
            tv.tv_usec = 0;
            sel = select(rp[0] + 1, &rfds, NULL, NULL, &tv);
            if (sel <= 0 || read(rp[0], &rb, 1) != 1) {
                fprintf(stderr,
                        "origin server did not report readiness within 5s "
                        "(select=%d, errno=%s) —— 这是测试夹具失败，"
                        "不是被测产品回归\n", sel, strerror(errno));
                close(rp[0]);
                kill(origin, SIGKILL);
                waitpid(origin, NULL, 0);
                return 2;
            }
            close(rp[0]);
            if (rb != 'R') {
                int ost = 0;
                waitpid(origin, &ost, 0);
                fprintf(stderr,
                        "origin server failed to bind/listen on port %d "
                        "(exit status %d) —— 测试夹具失败，非产品回归\n",
                        ORIGIN_PORT, ost);
                return 2;
            }
        }
    }

    for (i = 0; i < nciphers; i++) {
        const char *m = ciphers[i];
        char sp[16], lp[16];
        char *sargv[16], *largv[16];
        int si = 0, li = 0;
        pid_t ps, pl;
        char body[2048];
        int rc, ok;

        snprintf(sp, sizeof(sp), "%d", SRV_PORT);
        snprintf(lp, sizeof(lp), "%d", LOC_PORT);

        sargv[si++] = ss_server;
        sargv[si++] = "-s"; sargv[si++] = "127.0.0.1";
        sargv[si++] = "-p"; sargv[si++] = sp;
        sargv[si++] = "-k"; sargv[si++] = (char *)PASSWORD;
        sargv[si++] = "-m"; sargv[si++] = (char *)m;
        sargv[si++] = "-u";
        sargv[si] = NULL;

        largv[li++] = ss_local;
        largv[li++] = "-s"; largv[li++] = "127.0.0.1";
        largv[li++] = "-p"; largv[li++] = sp;
        largv[li++] = "-l"; largv[li++] = lp;
        largv[li++] = "-k"; largv[li++] = (char *)PASSWORD;
        largv[li++] = "-m"; largv[li++] = (char *)m;
        largv[li++] = "-u";
        largv[li] = NULL;

        ps = spawn(ss_server, sargv);
        pl = spawn(ss_local, largv);

        if (ps <= 0 || pl <= 0) {
            /* fork 失败：如实记为 FAIL，且绝不对 -1 调 kill()。 */
            char why[128];
            snprintf(why, sizeof(why), "(fork failed: %s)", strerror(errno));
            report(m, "SOCKS5 tunnel round-trip", 0, why);
            reap(ps);
            reap(pl);
            continue;
        }

        sleep(2);

        body[0] = '\0';
        rc = socks5_get(LOC_PORT, "/", body, sizeof(body));
        ok = (rc == 0) && (strstr(body, ORIGIN_BODY) != NULL);
        report(m, "SOCKS5 tunnel round-trip", ok,
               ok ? "(payload matched)" : "(payload NOT matched)");

        reap(ps);
        reap(pl);
        sleep(1);
    }

    reap(origin);

    /* 汇总行是 conanfile.py 的解析契约：格式一行为
     *   E2E summary: <passed> passed, <failed> failed (ciphers=<n>)
     * 必须保持单行、可正则匹配，且显式 fflush（stdout 被重定向到文件时
     * 若进程异常退出会丢内容）。 */
    printf("\nE2E summary: %d passed, %d failed (ciphers=%zu)\n",
           g_pass, g_fail, nciphers);
    fflush(stdout);
    return g_fail == 0 ? 0 : 1;
}
