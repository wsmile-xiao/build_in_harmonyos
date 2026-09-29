/* test_package consumer test for rcon 0.6 (L1 + 鸿蒙特有测试/端到端消费者用例).
 *
 * Two layers:
 *  1) Smoke: run `rcon --help`, assert exit 0 + usage text (R34/PF3).
 *  2) End-to-end consumer case: start a minimal RCON server on 127.0.0.1,
 *     drive the packaged `rcon` binary through a REAL auth + command round
 *     trip over an actual TCP socket, and assert:
 *       - the server received a well-formed auth packet with the right password
 *       - the server received the command packet with the expected payload
 *       - the client printed the server's response body ("e2e-ok") and exited 0
 *     This is a complete consumer use case (not a pure assertion): it runs the
 *     installed binary end-to-end against the real RCON wire protocol.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define E2E_PASSWORD "hunter2-e2e"
#define E2E_COMMAND  "echo e2e-ok"
#define E2E_REPLY    "e2e-ok"
#define RECV_TIMEOUT_SEC 10

/* RCON wire types (mirror of srcrcon.h, value-level) */
#define RCON_AUTH         3
#define RCON_AUTH_RESP    2
#define RCON_COMMAND      2
#define RCON_RESP_VALUE   0

static int read_full(int fd, unsigned char *buf, size_t n)
{
    size_t got = 0;

    while (got < n) {
        ssize_t r = read(fd, buf + got, n - got);
        if (r <= 0) {
            return -1;
        }
        got += (size_t)r;
    }
    return 0;
}

static int write_full(int fd, const unsigned char *buf, size_t n)
{
    size_t done = 0;

    while (done < n) {
        ssize_t r = write(fd, buf + done, n - done);
        if (r <= 0) {
            return -1;
        }
        done += (size_t)r;
    }
    return 0;
}

/* Receive one RCON packet: 4-byte LE size + payload.
 * Payload = id(4) + type(4) + body + null + null. */
static int recv_packet(int fd, int32_t *id, int32_t *type,
                       unsigned char *body, size_t *bodylen, size_t cap)
{
    unsigned char hdr[4];
    unsigned char payload[1024];
    int32_t size = 0;
    size_t blen = 0;

    if (read_full(fd, hdr, 4) != 0) {
        return -1;
    }
    memcpy(&size, hdr, sizeof(size)); /* LE host (aarch64/x86_64) */
    if (size < 8 || (size_t)size > sizeof(payload)) {
        return -1;
    }
    if (read_full(fd, payload, (size_t)size) != 0) {
        return -1;
    }
    memcpy(id, payload, 4);
    memcpy(type, payload + 4, 4);
    blen = (size_t)size - 8 - 2; /* - id - type - two trailing nulls */
    if (blen > 0) {
        memcpy(body, payload + 8, blen);
    }
    *bodylen = blen;
    return 0;
}

static int send_packet(int fd, int32_t id, int32_t type, const char *body)
{
    unsigned char pkt[1024];
    size_t blen = strlen(body);
    int32_t size = (int32_t)(8 + blen + 2);
    size_t off = 0;

    memcpy(pkt + off, &size, 4); off += 4;
    memcpy(pkt + off, &id, 4);   off += 4;
    memcpy(pkt + off, &type, 4); off += 4;
    memcpy(pkt + off, body, blen); off += blen;
    pkt[off++] = 0;
    pkt[off++] = 0;

    return write_full(fd, pkt, off);
}

/* Fake RCON server (child process): validate the exact packet sequence the
 * real `rcon` client produces, reply per protocol, exit 0 on full success. */
static int run_server(int listen_fd)
{
    int cfd = -1;
    int32_t id = 0, type = 0;
    unsigned char body[1024];
    size_t blen = 0;
    struct timeval tv;

    cfd = accept(listen_fd, NULL, NULL);
    if (cfd < 0) {
        return 1;
    }
    tv.tv_sec = RECV_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(cfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    /* 1) auth packet: type 3, body == password */
    if (recv_packet(cfd, &id, &type, body, &blen, sizeof(body)) != 0) {
        return 2;
    }
    if (type != RCON_AUTH || blen != strlen(E2E_PASSWORD) ||
        memcmp(body, E2E_PASSWORD, blen) != 0) {
        return 3;
    }
    if (send_packet(cfd, id, RCON_AUTH_RESP, "") != 0) {
        return 4;
    }

    /* 2) command packet: type 2, body == expected command */
    if (recv_packet(cfd, &id, &type, body, &blen, sizeof(body)) != 0) {
        return 5;
    }
    if (type != RCON_COMMAND || blen != strlen(E2E_COMMAND) ||
        memcmp(body, E2E_COMMAND, blen) != 0) {
        return 6;
    }
    if (send_packet(cfd, id, RCON_RESP_VALUE, E2E_REPLY) != 0) {
        return 7;
    }

    /* 3) empty command (client's end marker): type 2, empty body */
    if (recv_packet(cfd, &id, &type, body, &blen, sizeof(body)) != 0) {
        return 8;
    }
    if (type != RCON_COMMAND || blen != 0) {
        return 9;
    }
    if (send_packet(cfd, id, RCON_RESP_VALUE, "") != 0) {
        return 10;
    }

    close(cfd);
    return 0;
}

static int smoke_help(void)
{
    char buf[4096];
    FILE *pipe = NULL;
    int ok = 0;

    pipe = popen("rcon --help 2>&1", "r");
    if (pipe == NULL) {
        fprintf(stderr, "test_rcon: popen failed\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), pipe) != NULL) {
        if (strstr(buf, "Usage:") != NULL) {
            ok = 1;
        }
    }
    {
        int rc = pclose(pipe);
        if (rc != 0) {
            fprintf(stderr, "test_rcon: rcon --help exited with %d\n", rc);
            return 1;
        }
    }
    if (!ok) {
        fprintf(stderr, "test_rcon: rcon --help did not print usage\n");
        return 1;
    }
    printf("test_rcon: smoke (rcon --help) OK\n");
    return 0;
}

static int e2e_roundtrip(void)
{
    int lfd = -1;
    int rc = -1;
    int sr = 0;
    pid_t pid = -1;
    FILE *pipe = NULL;
    struct sockaddr_in sa;
    socklen_t alen = sizeof(sa);
    char cmdline[512];
    char out[4096];
    size_t used = 0;
    int server_rc = -1;

    lfd = socket(AF_INET, SOCK_STREAM, 0);
    if (lfd < 0) {
        fprintf(stderr, "test_rcon: socket() failed: %s\n", strerror(errno));
        return 1;
    }
    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    sa.sin_port = 0; /* ephemeral */
    if (bind(lfd, (struct sockaddr *)&sa, sizeof(sa)) != 0 ||
        listen(lfd, 4) != 0) {
        fprintf(stderr, "test_rcon: bind/listen failed: %s\n", strerror(errno));
        close(lfd);
        return 1;
    }
    if (getsockname(lfd, (struct sockaddr *)&sa, &alen) != 0) {
        fprintf(stderr, "test_rcon: getsockname failed: %s\n", strerror(errno));
        close(lfd);
        return 1;
    }

    pid = fork();
    if (pid < 0) {
        fprintf(stderr, "test_rcon: fork failed: %s\n", strerror(errno));
        close(lfd);
        return 1;
    }
    if (pid == 0) {
        int cret = run_server(lfd);
        _exit(cret);
    }
    close(lfd); /* parent no longer needs the listener */

    snprintf(cmdline, sizeof(cmdline),
             "rcon -H 127.0.0.1 -p %d -P %s %s 2>&1",
             ntohs(sa.sin_port), E2E_PASSWORD, E2E_COMMAND);

    pipe = popen(cmdline, "r");
    if (pipe == NULL) {
        fprintf(stderr, "test_rcon: popen(rcon e2e) failed\n");
        kill(pid, SIGKILL);
        waitpid(pid, NULL, 0);
        return 1;
    }
    while (used + 1 < sizeof(out) &&
           fgets(out + used, (int)(sizeof(out) - used), pipe) != NULL) {
        used += strlen(out + used);
    }
    rc = pclose(pipe);

    waitpid(pid, &sr, 0);
    server_rc = (WIFEXITED(sr) ? WEXITSTATUS(sr) : -1);

    if (rc != 0) {
        fprintf(stderr, "test_rcon: rcon exited %d (out=%s)\n", rc, out);
        return 1;
    }
    if (strstr(out, E2E_REPLY) == NULL) {
        fprintf(stderr, "test_rcon: client output missing %s: %s\n",
                E2E_REPLY, out);
        return 1;
    }
    if (server_rc != 0) {
        fprintf(stderr, "test_rcon: server saw wrong traffic (server rc=%d)\n",
                server_rc);
        return 1;
    }

    printf("test_rcon: e2e OK (auth+command round trip on 127.0.0.1:%d)\n",
           ntohs(sa.sin_port));
    return 0;
}

int main(void)
{
    int r = 0;

    alarm(60); /* hard cap: fail loudly instead of hanging CI */

    r = smoke_help();
    if (r != 0) {
        return r;
    }
    r = e2e_roundtrip();
    if (r != 0) {
        return r;
    }

    printf("test_rcon: ALL OK\n");
    return 0;
}
