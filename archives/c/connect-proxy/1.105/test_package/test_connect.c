/* test_connect.c — test_package for connect-proxy 1.105 (R34).
 *
 * connect is a CLI relay tool, not a library, so the test drives the
 * installed binary end-to-end: it starts an in-process TCP server on
 * 127.0.0.1, spawns `connect` with its stdin/stdout wired to pipes, and
 * verifies each relay method actually speaks its protocol and relays data.
 *
 * Cases:
 *   1. connect -V                 → prints "Version 1.105"
 *   2. connect -n HOST PORT       → direct TCP relay (stdio <-> socket)
 *   3. connect -H proxy HOST PORT → HTTP CONNECT tunnel handshake + relay
 *   4. connect -5 -S proxy ...    → SOCKS5 handshake + relay
 *
 * The binary path is passed as argv[1] by test_package/conanfile.py, so the
 * test fails (exec/handshake failure) when the package artifacts are removed
 * — required by the CI L1e destructive negative test.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define DEST_HOST "example.invalid"
#define DEST_PORT 12345
#define TEST_TIMEOUT 60
#define IO_TIMEOUT   15

static const char *connect_bin = NULL;
static int failures = 0;

static void on_timeout(int sig)
{
    (void)sig;
    fprintf(stderr, "FAIL: test timed out after %d seconds\n", TEST_TIMEOUT);
    _exit(1);
}

static void check(int ok, const char *what)
{
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

/* Bound the blocking accept()/read() calls so that a connect-proxy binary which dies
 * on startup surfaces as a clear error instead of stalling until the alarm. */
static void set_rcv_timeout(int fd)
{
    struct timeval tv;

    tv.tv_sec = IO_TIMEOUT;
    tv.tv_usec = 0;
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
}

/* Reap the child and describe how it died — the reason a case failed is
 * usually in connect's own exit status, not in our socket bookkeeping. */
static void report_child(pid_t pid)
{
    int status;

    if (waitpid(pid, &status, WNOHANG) == pid) {
        if (WIFEXITED(status))
            printf("  [connect exited with status %d]\n", WEXITSTATUS(status));
        else if (WIFSIGNALED(status))
            printf("  [connect killed by signal %d]\n", WTERMSIG(status));
    }
}

/* accept() with a bound wait: SO_RCVTIMEO is not honoured by accept() on every
 * platform, so wait for readability explicitly. Returns -1 if connect never
 * connected (it most likely died on startup). */
static int accept_timeout(int lfd)
{
    struct pollfd pfd;

    pfd.fd = lfd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    if (poll(&pfd, 1, IO_TIMEOUT * 1000) <= 0)
        return -1;
    return accept(lfd, NULL, NULL);
}

/* Listen on 127.0.0.1 with a kernel-assigned port. */
static int listen_local(int *port)
{
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    int one = 1;
    int fd = socket(AF_INET, SOCK_STREAM, 0);

    if (fd < 0)
        return -1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    set_rcv_timeout(fd);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0 ||
        listen(fd, 1) < 0 ||
        getsockname(fd, (struct sockaddr *)&addr, &len) < 0) {
        close(fd);
        return -1;
    }
    *port = ntohs(addr.sin_port);
    return fd;
}

/* Spawn connect with stdin/stdout attached to pipes. */
static pid_t spawn_connect(char *const argv[], int *to_child, int *from_child)
{
    int in_pipe[2], out_pipe[2];
    pid_t pid;

    if (pipe(in_pipe) < 0)
        return -1;
    if (pipe(out_pipe) < 0) {
        close(in_pipe[0]);
        close(in_pipe[1]);
        return -1;
    }
    pid = fork();
    if (pid < 0) {
        close(in_pipe[0]);
        close(in_pipe[1]);
        close(out_pipe[0]);
        close(out_pipe[1]);
        return -1;
    }
    if (pid == 0) {
        dup2(in_pipe[0], STDIN_FILENO);
        dup2(out_pipe[1], STDOUT_FILENO);
        close(in_pipe[0]);
        close(in_pipe[1]);
        close(out_pipe[0]);
        close(out_pipe[1]);
        execv(connect_bin, argv);
        fprintf(stderr, "execv(%s) failed: %s\n", connect_bin, strerror(errno));
        _exit(127);
    }
    close(in_pipe[0]);
    close(out_pipe[1]);
    *to_child = in_pipe[1];
    *from_child = out_pipe[0];
    return pid;
}

static int read_exact(int fd, void *buf, size_t n)
{
    size_t got = 0;
    while (got < n) {
        ssize_t r = read(fd, (char *)buf + got, n - got);
        if (r <= 0)
            return -1;
        got += (size_t)r;
    }
    return 0;
}

/* Read a CRLF-terminated line (without terminating NUL guarantees beyond size). */
static int read_line(int fd, char *buf, size_t size)
{
    size_t i = 0;
    while (i + 1 < size) {
        char c;
        if (read_exact(fd, &c, 1) < 0)
            return -1;
        buf[i++] = c;
        if (c == '\n')
            break;
    }
    buf[i] = '\0';
    return (int)i;
}

/* Send "PING" through connect to the peer, answer "PONG", read it back. */
static int check_relay(int peer, int to_child, int from_child)
{
    char buf[16];

    if (write(to_child, "PING\n", 5) != 5)
        return -1;
    memset(buf, 0, sizeof(buf));
    if (read_exact(peer, buf, 5) < 0 || memcmp(buf, "PING\n", 5) != 0)
        return -1;
    if (write(peer, "PONG\n", 5) != 5)
        return -1;
    memset(buf, 0, sizeof(buf));
    if (read_exact(from_child, buf, 5) < 0 || memcmp(buf, "PONG\n", 5) != 0)
        return -1;
    return 0;
}

static void finish_child(pid_t pid, int to_child, int from_child, int peer)
{
    int status;

    close(to_child);   /* EOF on stdin makes connect exit */
    close(from_child);
    if (peer >= 0)
        close(peer);
    kill(pid, SIGTERM);
    waitpid(pid, &status, 0);
}

/* Case 1: connect -V prints the version banner on stderr. */
static void test_version(void)
{
    char cmd[1024];
    char line[256];
    int found = 0;
    FILE *fp;

    snprintf(cmd, sizeof(cmd), "\"%s\" -V 2>&1", connect_bin);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        check(0, "connect -V (popen failed)");
        return;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        printf("  [connect -V] %s", line);
        if (strstr(line, "Version 1.105") != NULL)
            found = 1;
    }
    pclose(fp);
    check(found, "connect -V reports \"Version 1.105\"");
}

/* Case 2: direct relay (-n) — connect talks plain TCP to the destination. */
static void test_direct_relay(void)
{
    char port_str[16];
    char *argv[5];
    int lfd, port, peer, to_child, from_child;
    pid_t pid;

    lfd = listen_local(&port);
    if (lfd < 0) {
        check(0, "direct relay (listen failed)");
        return;
    }
    snprintf(port_str, sizeof(port_str), "%d", port);
    argv[0] = (char *)"connect";
    argv[1] = (char *)"-n";
    argv[2] = (char *)"127.0.0.1";
    argv[3] = port_str;
    argv[4] = NULL;

    pid = spawn_connect(argv, &to_child, &from_child);
    if (pid < 0) {
        close(lfd);
        check(0, "direct relay (fork failed)");
        return;
    }
    peer = accept_timeout(lfd);
    close(lfd);
    if (peer < 0) {
        report_child(pid);
        check(0, "direct relay (connect never connected)");
        finish_child(pid, to_child, from_child, -1);
        return;
    }
    set_rcv_timeout(peer);
    check(check_relay(peer, to_child, from_child) == 0,
          "connect -n relays stdio <-> TCP (direct mode)");
    finish_child(pid, to_child, from_child, peer);
}

/* Case 3: HTTP CONNECT tunnel (-H) against an in-process HTTP proxy. */
static void test_http_tunnel(void)
{
    char proxy[64];
    char dest_port[16];
    char line[512];
    char expected[128];
    char *argv[7];
    int lfd, port, peer, to_child, from_child;
    pid_t pid;

    lfd = listen_local(&port);
    if (lfd < 0) {
        check(0, "http tunnel (listen failed)");
        return;
    }
    snprintf(proxy, sizeof(proxy), "127.0.0.1:%d", port);
    snprintf(dest_port, sizeof(dest_port), "%d", DEST_PORT);
    argv[0] = (char *)"connect";
    argv[1] = (char *)"-H";
    argv[2] = proxy;
    argv[3] = (char *)DEST_HOST;
    argv[4] = dest_port;
    argv[5] = NULL;

    pid = spawn_connect(argv, &to_child, &from_child);
    if (pid < 0) {
        close(lfd);
        check(0, "http tunnel (fork failed)");
        return;
    }
    peer = accept_timeout(lfd);
    close(lfd);
    if (peer < 0) {
        report_child(pid);
        check(0, "http tunnel (connect never connected)");
        finish_child(pid, to_child, from_child, -1);
        return;
    }
    set_rcv_timeout(peer);

    /* Request line must be: CONNECT example.invalid:12345 HTTP/1.0 */
    snprintf(expected, sizeof(expected), "CONNECT %s:%d HTTP/1.0", DEST_HOST, DEST_PORT);
    if (read_line(peer, line, sizeof(line)) < 0) {
        check(0, "http tunnel (no CONNECT request)");
        finish_child(pid, to_child, from_child, peer);
        return;
    }
    printf("  [proxy <<] %s", line);
    check(strncmp(line, expected, strlen(expected)) == 0,
          "connect -H sends a well-formed HTTP CONNECT request");

    /* Drain the remaining request headers up to the blank line. */
    while (read_line(peer, line, sizeof(line)) > 0) {
        if (strcmp(line, "\r\n") == 0 || strcmp(line, "\n") == 0)
            break;
    }
    {
        static const char ok_response[] = "HTTP/1.0 200 Connection established\r\n\r\n";
        size_t len = strlen(ok_response);
        if (write(peer, ok_response, len) != (ssize_t)len) {
            check(0, "http tunnel (failed to send 200 response)");
            finish_child(pid, to_child, from_child, peer);
            return;
        }
    }
    check(check_relay(peer, to_child, from_child) == 0,
          "connect -H relays payload after the tunnel is established");
    finish_child(pid, to_child, from_child, peer);
}

/* Case 4: SOCKS5 (-5 -S) against an in-process SOCKS5 server. */
static void test_socks5_relay(void)
{
    unsigned char greeting[2];
    unsigned char methods[255];
    unsigned char request[4];
    unsigned char host_len;
    unsigned char reply[10];
    char host[256];
    char proxy[64];
    char dest_port[16];
    char *argv[9];
    int lfd, port, peer, to_child, from_child;
    unsigned int dport;
    unsigned char port_bytes[2];
    pid_t pid;

    lfd = listen_local(&port);
    if (lfd < 0) {
        check(0, "socks5 relay (listen failed)");
        return;
    }
    snprintf(proxy, sizeof(proxy), "127.0.0.1:%d", port);
    snprintf(dest_port, sizeof(dest_port), "%d", DEST_PORT);
    /* -R remote: let the SOCKS server resolve the name (ATYP=3), no local DNS */
    argv[0] = (char *)"connect";
    argv[1] = (char *)"-5";
    argv[2] = (char *)"-R";
    argv[3] = (char *)"remote";
    argv[4] = (char *)"-S";
    argv[5] = proxy;
    argv[6] = (char *)DEST_HOST;
    argv[7] = dest_port;
    argv[8] = NULL;

    pid = spawn_connect(argv, &to_child, &from_child);
    if (pid < 0) {
        close(lfd);
        check(0, "socks5 relay (fork failed)");
        return;
    }
    peer = accept_timeout(lfd);
    close(lfd);
    if (peer < 0) {
        report_child(pid);
        check(0, "socks5 relay (connect never connected)");
        finish_child(pid, to_child, from_child, -1);
        return;
    }
    set_rcv_timeout(peer);

    /* Method negotiation: VER=5, NMETHODS, METHODS... → reply NO-AUTH. */
    if (read_exact(peer, greeting, 2) < 0 || greeting[0] != 5 ||
        read_exact(peer, methods, greeting[1]) < 0) {
        check(0, "socks5 relay (bad method negotiation)");
        finish_child(pid, to_child, from_child, peer);
        return;
    }
    reply[0] = 5;
    reply[1] = 0; /* NO AUTHENTICATION REQUIRED */
    if (write(peer, reply, 2) != 2) {
        check(0, "socks5 relay (failed to answer method negotiation)");
        finish_child(pid, to_child, from_child, peer);
        return;
    }

    /* CONNECT request: VER=5, CMD=1, RSV=0, ATYP=3 (domain name). */
    if (read_exact(peer, request, 4) < 0 ||
        read_exact(peer, &host_len, 1) < 0 ||
        read_exact(peer, host, host_len) < 0 ||
        read_exact(peer, port_bytes, 2) < 0) {
        check(0, "socks5 relay (bad CONNECT request)");
        finish_child(pid, to_child, from_child, peer);
        return;
    }
    host[host_len] = '\0';
    dport = (unsigned int)((port_bytes[0] << 8) | port_bytes[1]);
    printf("  [socks5 <<] ver=%u cmd=%u atyp=%u host=%s port=%u\n",
           request[0], request[1], request[3], host, dport);
    check(request[0] == 5 && request[1] == 1 && request[3] == 3 &&
              strcmp(host, DEST_HOST) == 0 && dport == DEST_PORT,
          "connect -5 sends a SOCKS5 CONNECT request with remote name resolution");

    /* Reply: succeeded, bound to 0.0.0.0:0 */
    memset(reply, 0, sizeof(reply));
    reply[0] = 5; /* VER */
    reply[1] = 0; /* REP: succeeded */
    reply[3] = 1; /* ATYP: IPv4 */
    if (write(peer, reply, 10) != 10) {
        check(0, "socks5 relay (failed to send reply)");
        finish_child(pid, to_child, from_child, peer);
        return;
    }
    check(check_relay(peer, to_child, from_child) == 0,
          "connect -5 relays payload after the SOCKS5 handshake");
    finish_child(pid, to_child, from_child, peer);
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-connect-binary>\n", argv[0]);
        return 1;
    }
    connect_bin = argv[1];
    setvbuf(stdout, NULL, _IOLBF, 0); /* keep progress visible in CI logs */
    printf("Testing connect-proxy binary: %s\n", connect_bin);

    signal(SIGPIPE, SIG_IGN);
    signal(SIGALRM, on_timeout);
    alarm(TEST_TIMEOUT);

    test_version();
    test_direct_relay();
    test_http_tunnel();
    test_socks5_relay();

    if (failures != 0) {
        printf("%d test(s) failed\n", failures);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
