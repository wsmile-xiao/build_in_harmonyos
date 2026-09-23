/* test_micro_inetd.c — consumer-side verification of the installed micro_inetd.
 *
 * micro_inetd is an inetd-style spawner: it listens on one port and, for
 * every accepted connection, forks a child in which the connected socket
 * is dup2()ed onto stdin/stdout/stderr before execv()ing the service
 * program. This driver exercises that contract against the FINAL INSTALLED
 * binary, not a build-tree copy:
 *
 *   T1  request/response   — service relays bytes back over the socket
 *                            (stdin AND stdout are wired to the socket)
 *   T2  exit status        — service exits 42; connection gets EOF, spawner
 *                            survives and still accepts new connections
 *   T3  concurrency        — 4 sockets open at once, interleaved
 *                            request/response on each, all independent
 *   T4  repeated connects  — 5 sequential rounds of fresh connections while
 *                            the spawner keeps running (nowait semantics)
 *   T5  invalid command    — spawner configured with /nonexistent/prog:
 *                            connect must succeed (accept+fork happen) but
 *                            the client sees immediate EOF (execv failed)
 *   T6  usage              — no args: prints usage on stderr, exits 1
 *
 * Test services are built alongside this driver (svc_cat, svc_exit42) so
 * the test never depends on any system binary beyond libc.
 *
 * Safety: only unprivileged high ports on 127.0.0.1, no root, no systemd,
 * no background daemons. The spawner runs as a foreground child of this
 * process and is reaped on every exit path (SIGTERM, then bounded waitpid,
 * then SIGKILL fallback). See stop_spawner().
 */

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *g_inetd;      /* installed micro_inetd path */
static const char *g_svc_cat;    /* svc_cat path */
static const char *g_svc_exit42; /* svc_exit42 path */

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

static int connect_to(unsigned short port, int timeout_ms);

/* ------------------------------------------------------------------ */
/* Port / process management                                           */
/* ------------------------------------------------------------------ */

/* Ask the kernel for a free high port by binding an ephemeral socket.
 * Returns 0 on failure. The port is released before returning; the small
 * race window is handled by bring_up() which fails loudly if the spawner
 * cannot bind, instead of hanging. */
static unsigned short pick_free_port(void)
{
    struct sockaddr_in a;
    socklen_t alen = sizeof(a);
    unsigned short port = 0;

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 0;

    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = 0; /* kernel-assigned ephemeral */

    if (bind(fd, (struct sockaddr *)&a, sizeof(a)) == 0 &&
        getsockname(fd, (struct sockaddr *)&a, &alen) == 0) {
        port = ntohs(a.sin_port);
    }
    close(fd);
    return port;
}

/* Fork+exec micro_inetd <port> <prog> and wait until its port accepts
 * connections (bounded). Returns pid (>0) on success, -1 on failure
 * (in which case the child, if any, is already reaped or never spawned). */
static pid_t bring_up(unsigned short port, const char *prog)
{
    char portstr[16];
    int st;
    pid_t pid;

    snprintf(portstr, sizeof(portstr), "%u", (unsigned)port);

    pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        /* Child: micro_inetd runs in the foreground; it never daemonizes. */
        execl(g_inetd, g_inetd, portstr, prog, (char *)0);
        _exit(127); /* exec failed */
    }

    /* Parent: poll-connect until the listener is ready (max ~2 s). */
    for (int i = 0; i < 40; i++) {
        int probe = connect_to(port, 0);
        if (probe >= 0) {
            close(probe);
            return pid;
        }
        /* Child already dead? (e.g. bind failed) */
        if (waitpid(pid, &st, WNOHANG) == pid) return -1;
        usleep(50 * 1000);
    }
    return -1;
}

/* Stop the spawner: SIGTERM, bounded waitpid, then SIGKILL as fallback.
 * Returns 0 on clean stop, -1 on timeout/leak (caller fails the test). */
static int stop_spawner(pid_t pid)
{
    int status;

    if (pid <= 0) return -1;
    if (kill(pid, SIGTERM) == 0) {
        for (int i = 0; i < 40; i++) { /* up to ~2 s */
            if (waitpid(pid, &status, WNOHANG) == pid) return 0;
            usleep(50 * 1000);
        }
    }
    /* Last resort. Reap blocking; a dead child cannot escape this. */
    kill(pid, SIGKILL);
    if (waitpid(pid, &status, 0) == pid) return 0;
    return -1;
}

/* ------------------------------------------------------------------ */
/* Socket helpers                                                      */
/* ------------------------------------------------------------------ */

static int connect_to(unsigned short port, int timeout_ms)
{
    struct sockaddr_in a;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;

    if (timeout_ms > 0) {
        fcntl(fd, F_SETFL, O_NONBLOCK);
    }

    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(port);

    if (connect(fd, (struct sockaddr *)&a, sizeof(a)) < 0) {
        if (errno != EINPROGRESS) {
            close(fd);
            return -1;
        }
        fd_set wset;
        FD_ZERO(&wset);
        FD_SET(fd, &wset);
        struct timeval tv;
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        if (select(fd + 1, NULL, &wset, NULL, &tv) <= 0) {
            close(fd);
            return -1;
        }
        int soerr = 0;
        socklen_t slen = sizeof(soerr);
        if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &soerr, &slen) < 0 || soerr != 0) {
            close(fd);
            return -1;
        }
        fcntl(fd, F_SETFL, 0); /* back to blocking mode */
    }
    return fd;
}

static int send_all(int fd, const char *buf, size_t len)
{
    size_t off = 0;
    while (off < len) {
        ssize_t w = write(fd, buf + off, len - off);
        if (w < 0) return -1;
        off += (size_t)w;
    }
    return 0;
}

/* Read exactly expect bytes. 0 on success, -1 on EOF/error/timeout. */
static int recv_exact(int fd, char *buf, size_t expect, int timeout_ms)
{
    size_t got = 0;
    while (got < expect) {
        fd_set rset;
        FD_ZERO(&rset);
        FD_SET(fd, &rset);
        struct timeval tv;
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        if (select(fd + 1, &rset, NULL, NULL, &tv) <= 0) return -1;
        ssize_t n = read(fd, buf + got, expect - got);
        if (n <= 0) return -1;
        got += (size_t)n;
    }
    return 0;
}

/* Expect EOF: readable within timeout AND read() returns 0. */
static int expect_eof(int fd, int timeout_ms)
{
    fd_set rset;
    char c;
    ssize_t n;

    FD_ZERO(&rset);
    FD_SET(fd, &rset);
    struct timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    if (select(fd + 1, &rset, NULL, NULL, &tv) <= 0) return -1;
    n = read(fd, &c, 1);
    return (n == 0) ? 0 : -1;
}

/* ------------------------------------------------------------------ */
/* Test cases                                                          */
/* ------------------------------------------------------------------ */

/* T1: request/response — write bytes, read the same bytes back. */
static int test_relay_request_response(void)
{
    unsigned short port = pick_free_port();
    if (port == 0) {
        fprintf(stderr, "T1: no free port\n");
        return 1;
    }

    pid_t sp = bring_up(port, g_svc_cat);
    if (sp < 0) {
        fprintf(stderr, "T1: spawner bring-up failed\n");
        return 1;
    }

    static const char *msgs[] = {
        "hello micro_inetd",
        "second line of request",
        "x", /* tiny, tests small read/write */
        "a longer payload to force at least one more read() call on the socket, exercising the loop in svc_cat",
    };

    int failures = 0;
    int fd = connect_to(port, 5000);
    if (fd < 0) {
        fprintf(stderr, "T1: connect failed: %s\n", strerror(errno));
        failures++;
    } else {
        char buf[256];
        for (size_t i = 0; i < ARRAY_LEN(msgs); i++) {
            size_t len = strlen(msgs[i]);
            if (send_all(fd, msgs[i], len) < 0) {
                fprintf(stderr, "T1: send %zu failed\n", i);
                failures++;
                break;
            }
            memset(buf, 0, sizeof(buf));
            if (recv_exact(fd, buf, len, 5000) < 0) {
                fprintf(stderr, "T1: recv %zu failed\n", i);
                failures++;
                break;
            }
            if (memcmp(buf, msgs[i], len) != 0) {
                fprintf(stderr, "T1: payload %zu mismatch\n", i);
                failures++;
                break;
            }
        }
        close(fd);
    }

    if (stop_spawner(sp) < 0) failures++;
    printf("T1 request/response (relay over socket): %s\n", failures ? "FAIL" : "PASS");
    return failures;
}

/* T2: exit status — svc_exit42 exits 42; client sees EOF; spawner still
 * accepts afterwards (child reaping works, spawner survives). */
static int test_exit_status_and_survival(void)
{
    unsigned short port = pick_free_port();
    if (port == 0) {
        fprintf(stderr, "T2: no free port\n");
        return 1;
    }

    pid_t sp = bring_up(port, g_svc_exit42);
    if (sp < 0) {
        fprintf(stderr, "T2: spawner bring-up failed\n");
        return 1;
    }

    int failures = 0;
    for (int round = 0; round < 3; round++) {
        int fd = connect_to(port, 5000);
        if (fd < 0) {
            fprintf(stderr, "T2: round %d connect failed\n", round);
            failures++;
            continue;
        }
        /* Service exits immediately; its dup2()ed socket fds close -> EOF. */
        if (expect_eof(fd, 5000) < 0) {
            fprintf(stderr, "T2: round %d expected EOF\n", round);
            failures++;
        }
        close(fd);
    }

    if (stop_spawner(sp) < 0) failures++;
    printf("T2 exit status (service exit 42 -> EOF, spawner survives 3 rounds): %s\n",
           failures ? "FAIL" : "PASS");
    return failures;
}

/* T3: concurrency — 4 simultaneous connections, interleaved I/O. */
static int test_concurrent_connections(void)
{
    unsigned short port = pick_free_port();
    if (port == 0) {
        fprintf(stderr, "T3: no free port\n");
        return 1;
    }

    pid_t sp = bring_up(port, g_svc_cat);
    if (sp < 0) {
        fprintf(stderr, "T3: spawner bring-up failed\n");
        return 1;
    }

    enum { NCONN = 4, NROUNDS = 3 };
    int fds[NCONN];
    int failures = 0;

    for (int i = 0; i < NCONN; i++) {
        fds[i] = connect_to(port, 5000);
        if (fds[i] < 0) {
            fprintf(stderr, "T3: connect %d failed\n", i);
            failures++;
            break;
        }
    }

    for (int r = 0; r < NROUNDS && !failures; r++) {
        for (int i = 0; i < NCONN && !failures; i++) {
            char req[64], buf[64];
            int n = snprintf(req, sizeof(req), "conn%d-round%d", i, r);
            if (send_all(fds[i], req, (size_t)n) < 0 ||
                recv_exact(fds[i], buf, (size_t)n, 5000) < 0 ||
                memcmp(buf, req, (size_t)n) != 0) {
                fprintf(stderr, "T3: conn %d round %d failed\n", i, r);
                failures++;
            }
        }
    }

    for (int i = 0; i < NCONN; i++) {
        if (fds[i] >= 0) close(fds[i]);
    }

    if (stop_spawner(sp) < 0) failures++;
    printf("T3 concurrency (4 simultaneous connections x 3 interleaved rounds): %s\n",
           failures ? "FAIL" : "PASS");
    return failures;
}

/* T4: repeated connects — fresh connection rounds over spawner lifetime. */
static int test_repeated_connects(void)
{
    unsigned short port = pick_free_port();
    if (port == 0) {
        fprintf(stderr, "T4: no free port\n");
        return 1;
    }

    pid_t sp = bring_up(port, g_svc_cat);
    if (sp < 0) {
        fprintf(stderr, "T4: spawner bring-up failed\n");
        return 1;
    }

    int failures = 0;
    for (int round = 0; round < 5; round++) {
        int fd = connect_to(port, 5000);
        if (fd < 0) {
            fprintf(stderr, "T4: round %d connect failed\n", round);
            failures++;
            continue;
        }
        char req[32], buf[32];
        int n = snprintf(req, sizeof(req), "repeat-%d", round);
        if (send_all(fd, req, (size_t)n) < 0 ||
            recv_exact(fd, buf, (size_t)n, 5000) < 0 ||
            memcmp(buf, req, (size_t)n) != 0) {
            fprintf(stderr, "T4: round %d relay failed\n", round);
            failures++;
        }
        close(fd);
        usleep(20 * 1000); /* let SIGCHLD reap the previous child */
    }

    if (stop_spawner(sp) < 0) failures++;
    printf("T4 repeated connects (5 sequential rounds, one spawner): %s\n",
           failures ? "FAIL" : "PASS");
    return failures;
}

/* T5: invalid command — /nonexistent prog: connect OK; because the child's
 * stderr was dup2()ed onto the socket, the execv failure message travels
 * back over the connection (inetd semantics), then the child exits and
 * the client sees EOF. Spawner itself stays alive. */
static int test_invalid_command(void)
{
    unsigned short port = pick_free_port();
    if (port == 0) {
        fprintf(stderr, "T5: no free port\n");
        return 1;
    }

    pid_t sp = bring_up(port, "/nonexistent/micro_inetd_test_prog");
    if (sp < 0) {
        fprintf(stderr, "T5: spawner bring-up failed\n");
        return 1;
    }

    int failures = 0;
    int fd = connect_to(port, 5000);
    if (fd < 0) {
        fprintf(stderr, "T5: connect failed\n");
        failures++;
    } else {
        /* The child dup2()s the socket onto stderr, so execv's error
         * message is relayed to the client, followed by EOF on exit. */
        char buf[256];
        memset(buf, 0, sizeof(buf));
        ssize_t total = 0;
        while (total < (ssize_t)sizeof(buf) - 1) {
            fd_set rset;
            FD_ZERO(&rset);
            FD_SET(fd, &rset);
            struct timeval tv;
            tv.tv_sec = 5;
            tv.tv_usec = 0;
            if (select(fd + 1, &rset, NULL, NULL, &tv) <= 0) break;
            ssize_t n = read(fd, buf + total, sizeof(buf) - 1 - (size_t)total);
            if (n <= 0) break;
            total += n;
        }
        if (total == 0) {
            /* No error text: demand at least EOF. */
            fprintf(stderr, "T5: expected execv error relay, got no data\n");
            failures++;
        } else if (strstr(buf, "execl") == NULL) {
            fprintf(stderr, "T5: expected 'execl' perror text, got: %.80s\n", buf);
            failures++;
        }
        /* And afterwards EOF must arrive (child exit closes the fds). */
        if (expect_eof(fd, 5000) < 0) {
            fprintf(stderr, "T5: expected EOF after error relay\n");
            failures++;
        }
        close(fd);
    }

    /* Spawner must survive the execv failure and still accept. */
    if (failures == 0) {
        int fd2 = connect_to(port, 5000);
        if (fd2 < 0) {
            fprintf(stderr, "T5: spawner did not survive execv failure\n");
            failures++;
        } else {
            close(fd2);
        }
    }

    if (stop_spawner(sp) < 0) failures++;
    printf("T5 invalid command (execv error relayed over socket + EOF + spawner survives): %s\n",
           failures ? "FAIL" : "PASS");
    return failures;
}

/* T6: usage — no args: usage text on stderr, exit code 1. */
static int test_usage(void)
{
    int failures = 0;
    int pipefd[2];
    if (pipe(pipefd) < 0) {
        fprintf(stderr, "T6: pipe failed\n");
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        return 1;
    }
    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], 2); /* stderr of the child into the pipe */
        close(pipefd[1]);
        execl(g_inetd, g_inetd, (char *)0); /* no args at all */
        _exit(127);
    }
    close(pipefd[1]);

    char buf[512];
    ssize_t total = 0;
    while (total < (ssize_t)sizeof(buf) - 1) {
        fd_set rset;
        FD_ZERO(&rset);
        FD_SET(pipefd[0], &rset);
        struct timeval tv;
        tv.tv_sec = 5;
        tv.tv_usec = 0;
        if (select(pipefd[0] + 1, &rset, NULL, NULL, &tv) <= 0) break;
        ssize_t n = read(pipefd[0], buf + total, sizeof(buf) - 1 - (size_t)total);
        if (n <= 0) break;
        total += n;
    }
    buf[total] = '\0';
    close(pipefd[0]);

    int status;
    if (waitpid(pid, &status, 0) != pid) {
        fprintf(stderr, "T6: waitpid failed\n");
        failures++;
    } else if (!WIFEXITED(status) || WEXITSTATUS(status) != 1) {
        fprintf(stderr, "T6: expected exit 1, got raw status 0x%x\n", status);
        failures++;
    } else if (strstr(buf, "usage") == NULL) {
        fprintf(stderr, "T6: usage text not found in stderr (got: %.80s)\n", buf);
        failures++;
    }

    printf("T6 usage (no args -> stderr usage + exit 1): %s\n", failures ? "FAIL" : "PASS");
    return failures;
}

int main(int argc, char *argv[])
{
    int failed;

    if (argc != 4) {
        fprintf(stderr, "usage: %s <micro_inetd> <svc_cat> <svc_exit42>\n", argv[0]);
        return 2;
    }
    g_inetd = argv[1];
    g_svc_cat = argv[2];
    g_svc_exit42 = argv[3];

    signal(SIGPIPE, SIG_IGN); /* socket write after close is not fatal */

    failed = 0;
    failed += test_relay_request_response();
    failed += test_exit_status_and_survival();
    failed += test_concurrent_connections();
    failed += test_repeated_connects();
    failed += test_invalid_command();
    failed += test_usage();

    printf("test_micro_inetd: %d failure(s)\n", failed);
    return failed ? 1 : 0;
}
