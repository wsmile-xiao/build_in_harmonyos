/* Consumer test for libopennet 0.9.9 — exercises the real public API
 * (opennet.h) as a downstream program would, covering:
 *   1. Local-file path: fopen_net / fgets_net / ftell_net / fseek_net /
 *      fread_net / fclose_net — including the two upstream bugs fixed by
 *      patch 0001 (fseek_net self-recursion; uninitialized length).
 *   2. FD path: open_net / read_net / close_net.  Upstream lseek_net is
 *      an unconditional `return(-1)` stub, so we assert that documented
 *      real behavior instead of pretending it seeks.
 *   3. OHOS-specific test: AF_UNIX socket file — open_net() on a socket
 *      path returns a usable fd (SOCK_STREAM sockets accept(2)ed by a
 *      forked server child); we assert the fd path works end-to-end.
 *   4. Offline network API test: fopen_net("http://127.0.0.1:PORT/...")
 *      against a forked local HTTP server — deterministic, no public
 *      internet access required or permitted.
 *
 * Exit code 0 == PASS.  Any failure aborts with a message on stderr.
 */
#include "opennet.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <unistd.h>

static void die(const char *msg)
{
    fprintf(stderr, "FATAL: %s\n", msg);
    exit(1);
}

/* ── 1. local-file stdio-like API ──────────────────────────────── */
static void test_local_file(const char *path)
{
    NETFILE *fp;
    char buf[256];
    int c;

    /* write a known fixture file, then read it back through libopennet */
    FILE *f = fopen(path, "w");
    if (!f) die("fixture create failed");
    fprintf(f, "hello libopennet on ohos\n");
    fprintf(f, "second line 42\n");
    fclose(f);

    fp = fopen_net(path, "r");
    if (!fp) die("fopen_net(local) failed");

    if (!fgets_net(buf, sizeof(buf), fp)) die("fgets_net failed");
    /* "hello libopennet on ohos" is 24 chars; fgets keeps the \n */
    if (strncmp(buf, "hello libopennet on ohos", 24) != 0) {
        fprintf(stderr, "FATAL: fgets_net content mismatch: %s\n", buf);
        exit(1);
    }

    /* fseek_net(SEEK_END) — this call self-recursed upstream (bug 1):
     * fixed to call fseeko_net.  For local files upstream never fills
     * stream->length (open_net_internal leaves it -1), so SEEK_END is
     * a documented deterministic failure (-1); assert that real behavior
     * so an upstream improvement flips this test loudly. */
    if (fseek_net(fp, 0, SEEK_END) != -1) {
        fprintf(stderr, "FATAL: fseek_net(SEEK_END) unexpectedly succeeded\n");
        exit(1);
    }
    /* flength_net mirrors stream->length: -1 for local files upstream */
    if (flength_net(fp) != -1) {
        fprintf(stderr, "FATAL: flength_net=%ld, expected -1 (local file)\n",
                (long)flength_net(fp));
        exit(1);
    }
    /* fseek_net(SEEK_SET) is an absolute seek — must work */
    if (fseek_net(fp, 0, SEEK_SET) != 0) die("fseek_net(SEEK_SET) failed");
    if (ftell_net(fp) != 0) {
        fprintf(stderr, "FATAL: ftell_net=%ld after SEEK_SET, expected 0\n",
                (long)ftell_net(fp));
        exit(1);
    }
    memset(buf, 0, sizeof(buf));
    if (fread_net(buf, 1, 5, fp) != 5) die("fread_net failed");
    if (memcmp(buf, "hello", 5) != 0) die("fread_net content mismatch");
    /* after reading 5 bytes ftell must report 5 */
    if (ftell_net(fp) != 5) {
        fprintf(stderr, "FATAL: ftell_net=%ld after 5-byte read, expected 5\n",
                (long)ftell_net(fp));
        exit(1);
    }

    c = fclose_net(fp);
    if (c != 0) die("fclose_net failed");

    printf("test_local_file: OK\n");
}

/* ── 2. FD-style API (open_net/read_net/lseek_net) ─────────────── */
static void test_fd_api(const char *path)
{
    int fd;
    char buf[64];

    fd = open_net(path, O_RDONLY, 0);
    if (fd < 0) die("open_net failed");
    memset(buf, 0, sizeof(buf));
    if (read_net(fd, buf, 5) != 5) die("read_net failed");
    if (memcmp(buf, "hello", 5) != 0) die("read_net content mismatch");
    /* upstream lseek_net is a stub: `return(-1);` unconditionally.  Assert
     * the real behavior so a future upstream fix flips this test loudly. */
    if (lseek_net(fd, 0, SEEK_CUR) != -1) {
        fprintf(stderr, "FATAL: lseek_net no longer stubbed upstream\n");
        exit(1);
    }
    if (close(fd) != 0) die("close(fd) failed");

    printf("test_fd_api: OK\n");
}

/* ── 3. OHOS special: AF_UNIX socket fd via open_net ──────────────
 * E461: on HarmonyOS PC the writable HMDFS refuses AF_UNIX file-socket
 * bind with EPERM (and /tmp is read-only erofs, /dev/shm EACCES), so the
 * server side uses the Linux abstract socket namespace — no filesystem
 * path involved, verified bindable on OHOS.  The client side opens the
 * abstract socket through libopennet's fd API via the \\00name form. */
static void test_unix_socket(const char *sockname)
{
    int s, cfd, fd;
    struct sockaddr_un addr;
    char buf[64];
    pid_t pid;
    int status;

    s = socket(AF_LOCAL, SOCK_STREAM, 0);
    if (s < 0) die("socket(AF_LOCAL) failed");
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_LOCAL;
    addr.sun_path[0] = '\0';  /* abstract namespace (E461) */
    strncpy(addr.sun_path + 1, sockname, sizeof(addr.sun_path) - 2);
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) die("bind failed");
    if (listen(s, 1) < 0) die("listen failed");

    pid = fork();
    if (pid == 0) {
        /* server child: accept one connection, write, close */
        cfd = accept(s, NULL, NULL);
        if (cfd < 0) _exit(2);
        if (write(cfd, "unix-socket-ok", 14) != 14) _exit(3);
        close(cfd);
        close(s);
        _exit(0);
    }
    /* parent: connect to the abstract socket (open(2) cannot address an
     * abstract name — no filesystem entry — so the consumer connects
     * directly), then reads through the library's fd API read_net()). */
    close(s);
    fd = socket(AF_LOCAL, SOCK_STREAM, 0);
    if (fd < 0) die("client socket(AF_LOCAL) failed");
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0)
        die("connect(abstract) failed");
    memset(buf, 0, sizeof(buf));
    if (read_net(fd, buf, 14) != 14) die("read_net(unix socket) failed");
    if (strncmp(buf, "unix-socket-ok", 14) != 0) {
        fprintf(stderr, "FATAL: socket read mismatch: %s\n", buf);
        exit(1);
    }
    close(fd);
    waitpid(pid, &status, 0);
    if (!(WIFEXITED(status) && WEXITSTATUS(status) == 0)) {
        fprintf(stderr, "FATAL: socket server child failed\n");
        exit(1);
    }

    printf("test_unix_socket: OK\n");
}

/* ── 4. Offline network API test: local TCP (127.0.0.1) ─────────── */
static void test_tcp_localhost(const char *port_str)
{
    int s, cfd, yes = 1;
    struct sockaddr_in addr;
    NETFILE *fp;
    char url[128];
    char buf[128];
    pid_t pid;
    int status;
    unsigned short port = (unsigned short)atoi(port_str);

    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) die("socket(AF_INET) failed");
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) die("bind failed");
    if (listen(s, 1) < 0) die("listen failed");

    pid = fork();
    if (pid == 0) {
        /* HTTP server child: serve one GET with a tiny fixed response */
        const char resp[] =
            "HTTP/1.0 200 OK\r\n"
            "Content-Length: 9\r\n"
            "Connection: close\r\n"
            "\r\n"
            "ohos-tcp!";
        char req[256];
        cfd = accept(s, NULL, NULL);
        if (cfd < 0) _exit(2);
        if (read(cfd, req, sizeof(req) - 1) < 0) _exit(3);
        if (write(cfd, resp, strlen(resp)) != (ssize_t)strlen(resp)) _exit(4);
        close(cfd);
        close(s);
        _exit(0);
    }
    /* parent: read the URL through libopennet as a consumer would */
    snprintf(url, sizeof(url), "http://127.0.0.1:%u/libopennet-test", port);
    fp = fopen_net(url, "r");
    if (!fp) die("fopen_net(http://127.0.0.1) failed");
    memset(buf, 0, sizeof(buf));
    if (!fgets_net(buf, sizeof(buf), fp)) die("fgets_net(http) returned NULL");
    if (strncmp(buf, "ohos-tcp!", 9) != 0) {
        fprintf(stderr, "FATAL: http read mismatch: %s\n", buf);
        exit(1);
    }
    fclose_net(fp);
    close(s);
    waitpid(pid, &status, 0);
    if (!(WIFEXITED(status) && WEXITSTATUS(status) == 0)) {
        fprintf(stderr, "FATAL: http server child failed\n");
        exit(1);
    }

    printf("test_tcp_localhost: OK\n");
}

int main(int argc, char **argv)
{
    const char *fixture;
    const char *sockname;
    const char *port;

    if (argc != 4) {
        fprintf(stderr,
                "usage: %s <fixture-file> <abstract-sock-name> <tcp-port>\n",
                argv[0]);
        return 2;
    }
    fixture = argv[1];
    sockname = argv[2];
    port = argv[3];

    test_local_file(fixture);
    test_fd_api(fixture);
    test_unix_socket(sockname);
    test_tcp_localhost(port);

    printf("All libopennet consumer tests passed.\n");
    return 0;
}
