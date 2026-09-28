/* test_package/pipehelper.c — pipexec consumer-test helper (OHOS).
 *
 * pipexec wires process trees together by exec'ing an absolute path
 * (execv, not execvp — see src/pipexec.c:250), so the consumer test must
 * provide its own child processes by absolute path.  Relying on /bin/echo,
 * /bin/cat ... would tie the test to a traditional /bin, which HarmonyOS does
 * not have (E165).  This single helper therefore covers every role the smoke
 * test needs; it is compiled for the target by CMake and, on OHOS, copied to a
 * writable non-HMDFS directory and self-signed before execution.
 *
 * Usage:
 *   pipehelper produce <n>                 write n deterministic bytes to stdout
 *   pipehelper pass                        copy stdin -> stdout unchanged
 *   pipehelper consume <path> [expected]   read stdin, write it to <path>,
 *                                          print the byte count; exit 4 if
 *                                          <expected> is given and differs
 *   pipehelper echo <args...>              print args joined by a single space
 *   pipehelper exit <code>                 exit with <code>
 *   pipehelper sleep <seconds>             sleep, then exit 0
 *   pipehelper abort-once <marker>         first run: create <marker> and die
 *                                          on SIGABRT; later runs: exit 0
 */
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int write_all(int fd, const char *buf, size_t len)
{
    size_t done = 0;
    while (done < len) {
        ssize_t written = write(fd, buf + done, len - done);
        if (written < 0)
            return -1;
        done += (size_t)written;
    }
    return 0;
}

/* Copy the whole of stdin to fd_out, returning the number of bytes moved. */
static long long copy_all(int fd_out)
{
    long long total = 0;
    char buf[4096];
    ssize_t got;
    while ((got = read(STDIN_FILENO, buf, sizeof buf)) > 0) {
        if (write_all(fd_out, buf, (size_t)got) != 0)
            return -1;
        total += got;
    }
    return got < 0 ? -1 : total;
}

static int do_produce(long long n)
{
    char buf[4096];
    long long produced = 0;
    while (produced < n) {
        size_t chunk = sizeof buf;
        if ((long long)chunk > n - produced)
            chunk = (size_t)(n - produced);
        for (size_t i = 0; i < chunk; i++)
            buf[i] = (char)((produced + (long long)i) * 31 + 7);
        if (write_all(STDOUT_FILENO, buf, chunk) != 0) {
            perror("pipehelper: produce write");
            return 1;
        }
        produced += (long long)chunk;
    }
    fprintf(stderr, "pipehelper: produced %lld bytes\n", produced);
    return 0;
}

static int do_consume(const char *path, int have_expected, long long expected)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        perror("pipehelper: consume open");
        return 1;
    }
    long long total = copy_all(fd);
    if (close(fd) != 0)
        perror("pipehelper: consume close");
    if (total < 0) {
        perror("pipehelper: consume read");
        return 1;
    }
    fprintf(stderr, "pipehelper: consumed %lld bytes\n", total);
    if (have_expected && total != expected) {
        fprintf(stderr, "pipehelper: expected %lld bytes, got %lld\n",
                expected, total);
        return 4;
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: pipehelper <produce|pass|consume|echo|exit> ...\n");
        return 2;
    }
    if (strcmp(argv[1], "produce") == 0) {
        if (argc != 3) {
            fprintf(stderr, "usage: pipehelper produce <n>\n");
            return 2;
        }
        return do_produce(strtoll(argv[2], NULL, 10));
    }
    if (strcmp(argv[1], "pass") == 0) {
        long long total = copy_all(STDOUT_FILENO);
        if (total < 0) {
            perror("pipehelper: pass");
            return 1;
        }
        return 0;
    }
    if (strcmp(argv[1], "consume") == 0) {
        if (argc != 3 && argc != 4) {
            fprintf(stderr, "usage: pipehelper consume <path> [expected]\n");
            return 2;
        }
        return do_consume(argv[2], argc == 4,
                          argc == 4 ? strtoll(argv[3], NULL, 10) : 0);
    }
    if (strcmp(argv[1], "echo") == 0) {
        for (int i = 2; i < argc; i++) {
            if (i > 2 && write_all(STDOUT_FILENO, " ", 1) != 0)
                return 1;
            if (write_all(STDOUT_FILENO, argv[i], strlen(argv[i])) != 0)
                return 1;
        }
        if (write_all(STDOUT_FILENO, "\n", 1) != 0)
            return 1;
        return 0;
    }
    if (strcmp(argv[1], "exit") == 0) {
        if (argc != 3) {
            fprintf(stderr, "usage: pipehelper exit <code>\n");
            return 2;
        }
        return (int)strtol(argv[2], NULL, 10);
    }
    if (strcmp(argv[1], "sleep") == 0) {
        if (argc != 3) {
            fprintf(stderr, "usage: pipehelper sleep <seconds>\n");
            return 2;
        }
        (void)sleep((unsigned)strtoul(argv[2], NULL, 10));
        return 0;
    }
    if (strcmp(argv[1], "abort-once") == 0) {
        if (argc != 3) {
            fprintf(stderr, "usage: pipehelper abort-once <marker>\n");
            return 2;
        }
        if (access(argv[2], F_OK) == 0) {
            fprintf(stderr, "pipehelper: marker present, exiting 0\n");
            return 0;
        }
        int fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0)
            (void)close(fd);
        fprintf(stderr, "pipehelper: aborting to trigger pipexec restart\n");
        (void)raise(SIGABRT);
        return 1; /* unreachable if SIGABRT is fatal */
    }
    fprintf(stderr, "pipehelper: unknown mode '%s'\n", argv[1]);
    return 2;
}
