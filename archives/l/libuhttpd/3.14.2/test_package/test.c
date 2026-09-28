/*
 * Functional consumer test for libuhttpd 3.14.2.
 *
 * Starts a real uh_server on 127.0.0.1:<port> with a path handler, then runs
 * the libev loop in the main thread while a dedicated client thread performs
 * a real HTTP/1.1 GET over a socket, verifying status line and body. The
 * client must run in its own thread: the single-threaded event loop cannot
 * accept while the caller is blocked in recv() (deadlock otherwise).
 *
 * Exercises the installed library API (uh_server_new, add_path_handler,
 * listen, send_head/send_header/end_headers/printf/end_response) and the
 * libev event loop, proving the package links and runs on the target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <ev.h>
#include <uhttpd/uhttpd.h>

static int test_port = 0;
static int test_passed = 0;
static char test_err[256] = "";

static void watchdog_break(struct ev_loop *loop, ev_timer *w, int revents)
{
    (void)w;
    (void)revents;
    if (!test_passed)
        snprintf(test_err, sizeof(test_err), "watchdog timeout fired");
    ev_break(loop, EVBREAK_ALL);
}

static void hello_handler(struct uh_connection *conn, int event)
{
    if (event != UH_EV_COMPLETE)
        return;

    conn->send_head(conn, HTTP_STATUS_OK, -1, NULL);
    conn->send_header(conn, "Content-Type", "text/plain");
    conn->end_headers(conn);
    conn->printf(conn, "Hello from libuhttpd %s", UHTTPD_VERSION_STRING);
    conn->end_response(conn);
}

static void do_client_request(struct ev_loop *loop)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    char req[128];
    char buf[4096];
    ssize_t n;
    int total = 0;
    int attempt;

    if (fd < 0) {
        snprintf(test_err, sizeof(test_err), "socket() failed: %s", strerror(errno));
        goto out;
    }

    /* The server may keep the connection open after the chunked response;
       do not block forever waiting for EOF: bound recv with a timeout. */
    {
        struct timeval tv;
        tv.tv_sec = 5;
        tv.tv_usec = 0;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)test_port);
    if (inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr) != 1) {
        snprintf(test_err, sizeof(test_err), "inet_pton failed");
        goto out;
    }

    /* retry connect briefly: the loop may still be starting the accept watcher */
    for (attempt = 0; attempt < 50; attempt++) {
        if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0)
            break;
        usleep(100000);
    }
    if (attempt == 50) {
        snprintf(test_err, sizeof(test_err), "connect() failed: %s", strerror(errno));
        goto out;
    }

    snprintf(req, sizeof(req),
             "GET /hello HTTP/1.1\r\n"
             "Host: 127.0.0.1\r\n"
             "User-Agent: conan-test\r\n"
             "Connection: close\r\n\r\n");
    if (send(fd, req, strlen(req), 0) != (ssize_t)strlen(req)) {
        snprintf(test_err, sizeof(test_err), "send() failed: %s", strerror(errno));
        goto out;
    }

    while (1) {
        n = recv(fd, buf + total, sizeof(buf) - total - 1, 0);
        if (n > 0) {
            total += (int)n;
            continue;
        }
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
            break;  /* recv timeout: response fully read, connection kept open */
        break;  /* n == 0 (EOF) or hard error */
    }
    if (total <= 0) {
        snprintf(test_err, sizeof(test_err), "recv() failed: %s", strerror(errno));
        goto out;
    }
    buf[total] = '\0';

    /* Verify status line and body */
    if (strstr(buf, "HTTP/1.1 200") == NULL) {
        snprintf(test_err, sizeof(test_err), "no 200 status in response: %s", buf);
        goto out;
    }
    if (strstr(buf, "Hello from libuhttpd 3.14.2") == NULL) {
        snprintf(test_err, sizeof(test_err), "missing body in response: %s", buf);
        goto out;
    }

    printf("client response: %.120s\n", buf);
    test_passed = 1;

out:
    if (fd >= 0)
        close(fd);
    ev_break(loop, EVBREAK_ALL);
}

static void *client_thread(void *arg)
{
    do_client_request((struct ev_loop *)arg);
    return NULL;
}

static int try_listen(struct uh_server *srv, int base_port)
{
    int i;
    for (i = 0; i < 20; i++) {
        char addr[64];
        snprintf(addr, sizeof(addr), "127.0.0.1:%d", base_port + i);
        if (srv->listen(srv, addr, false) == 1) {
            test_port = base_port + i;
            return 0;
        }
    }
    return -1;
}

int main(void)
{
    struct ev_loop *loop = EV_DEFAULT;
    struct uh_server *srv;
    struct ev_timer watchdog;
    pthread_t th;
    int rc;

    srv = uh_server_new(loop);
    if (!srv) {
        fprintf(stderr, "uh_server_new failed\n");
        return 1;
    }

    if (srv->add_path_handler(srv, "/hello", hello_handler) != 0) {
        fprintf(stderr, "add_path_handler failed\n");
        srv->free(srv);
        return 2;
    }

    /* pick a high, likely-free port range to avoid collisions */
    if (try_listen(srv, 38080) != 0) {
        fprintf(stderr, "listen failed on candidate ports\n");
        srv->free(srv);
        return 3;
    }
    printf("server listening on 127.0.0.1:%d\n", test_port);

    if (pthread_create(&th, NULL, client_thread, loop) != 0) {
        fprintf(stderr, "pthread_create failed\n");
        srv->free(srv);
        return 4;
    }

    ev_timer_init(&watchdog, watchdog_break, 20.0, 0.0);
    ev_timer_start(loop, &watchdog);

    ev_run(loop, 0);

    pthread_join(th, NULL);

    rc = test_passed ? 0 : 5;
    if (!test_passed && test_err[0])
        fprintf(stderr, "TEST FAILED: %s\n", test_err);

    srv->free(srv);
    return rc;
}
