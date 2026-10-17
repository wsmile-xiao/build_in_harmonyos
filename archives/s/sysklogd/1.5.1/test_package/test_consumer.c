/*
 * test_consumer.c -- a real consumer of the sysklogd 1.5.1 public log surface.
 *
 * sysklogd publishes no library, so "consuming" it means speaking its
 * documented wire protocol: a datagram on the AF_UNIX SOCK_DGRAM socket that
 * syslogd binds (relocatable via `-p <path>`), carrying "<PRI>text" where PRI
 * is facility|severity as defined by <sys/syslog.h>.
 *
 * This program performs that whole sequence and turns every step into an
 * exit status: socket(2), connect(2), send(2) completeness.  It is compiled
 * and run by test_runner.sh, which additionally asserts that the record this
 * program injected reappears in the log file the daemon was configured to
 * write -- i.e. the daemon really processed it, rather than the socket merely
 * existing.
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syslog.h>
#include <sys/un.h>
#include <unistd.h>

static int send_record(int fd, const char *buf, size_t len, const char *what)
{
    ssize_t n;

    n = send(fd, buf, len, 0);
    if (n < 0) {
        fprintf(stderr, "%s: send: %s\n", what, strerror(errno));
        return 1;
    }
    if ((size_t)n != len) {
        fprintf(stderr, "%s: short send: %zd of %zu bytes\n", what, n, len);
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *path, *marker, *mode;
    struct sockaddr_un sa;
    char buf[512];
    size_t len;
    int fd, pri, rc;

    if (argc != 4) {
        fprintf(stderr,
                "usage: test_consumer <socket-path> <marker> <single|multiline>\n");
        return 2;
    }
    path = argv[1];
    marker = argv[2];
    mode = argv[3];

    if (strlen(path) >= sizeof(sa.sun_path)) {
        fprintf(stderr, "socket path does not fit sun_path: %s\n", path);
        return 2;
    }

    /* The priority is assembled from the public constants rather than a magic
     * number, so a change in the facility/severity encoding breaks this test
     * instead of silently passing. */
    pri = LOG_USER | LOG_INFO;

    fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        fprintf(stderr, "socket: %s\n", strerror(errno));
        return 1;
    }

    memset(&sa, 0, sizeof(sa));
    sa.sun_family = AF_UNIX;
    strncpy(sa.sun_path, path, sizeof(sa.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        fprintf(stderr, "connect(%s): %s\n", path, strerror(errno));
        close(fd);
        return 1;
    }

    if (strcmp(mode, "single") == 0) {
        len = (size_t)snprintf(buf, sizeof(buf), "<%d>%s-single\n", pri, marker);
    } else if (strcmp(mode, "multiline") == 0) {
        /* Two embedded records in one datagram: syslogd's line splitter has
         * to log both, which is what the multi-line assertion checks. */
        len = (size_t)snprintf(buf, sizeof(buf),
                               "<%d>%s-multiline-1\n<%d>%s-multiline-2\n",
                               pri, marker, pri, marker);
    } else {
        fprintf(stderr, "unknown mode: %s\n", mode);
        close(fd);
        return 2;
    }

    if (len >= sizeof(buf)) {
        fprintf(stderr, "formatted record truncated, cannot test\n");
        close(fd);
        return 1;
    }

    rc = send_record(fd, buf, len, mode);
    close(fd);

    if (rc == 0)
        printf("delivered %zu bytes to %s (%s)\n", len, path, mode);
    return rc;
}
