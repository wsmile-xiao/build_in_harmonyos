/* Consumer test for purelibc 1.0.8 on OHOS (capture path).
 *
 * Exercises the documented capture contract end to end without stdio:
 * after _pure_start() installs a pure_syscall handler, the libc calls the
 * process issues are routed through purelibc to the handler as raw
 * syscalls. The handler answers the virtual file's open/write/close with
 * an in-memory backing store and forwards everything else to the original
 * libc syscall pointer returned by _pure_start(). Assertions check both
 * the return values seen by the caller and the bytes the library
 * delivered to the handler.
 *
 * Note: the stdio FILE layer is exercised separately; on OHOS it falls
 * through to libc (see notes.md), so this test uses purelibc's direct
 * syscall wrappers (open/write/close), which behave identically on
 * glibc and musl. */
#include <fcntl.h>
#include <purelibc.h>
#include <stdarg.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

#define VIRTUAL_FD 100
#define VIRTUAL_PATH "/mem/virtual.txt"

static sfun g_orig_syscall;
static char g_backing[256];
static size_t g_backing_len;
static int g_write_calls;

static long pure_syscall(long sysno, ...)
{
    va_list ap;

    if (sysno == __NR_openat) {
        va_start(ap, sysno);
        (void)va_arg(ap, int);              /* dirfd (AT_FDCWD) */
        const char *path = va_arg(ap, const char *);
        va_end(ap);
        if (strcmp(path, VIRTUAL_PATH) == 0)
            return VIRTUAL_FD;
        return -1;                          /* nothing else is virtual */
    }

    if (sysno == __NR_write) {
        va_start(ap, sysno);
        int fd = va_arg(ap, int);
        const char *buf = va_arg(ap, const char *);
        size_t count = va_arg(ap, size_t);
        va_end(ap);
        if (fd == VIRTUAL_FD) {
            if (g_backing_len + count < sizeof(g_backing)) {
                memcpy(g_backing + g_backing_len, buf, count);
                g_backing_len += count;
                g_backing[g_backing_len] = '\0';
            }
            g_write_calls++;
            return (long)count;
        }
        return g_orig_syscall(sysno, fd, buf, count);
    }

    if (sysno == __NR_close || sysno == __NR_lseek) {
        va_start(ap, sysno);
        int fd = va_arg(ap, int);
        long a1 = va_arg(ap, long);
        long a2 = va_arg(ap, long);
        va_end(ap);
        if (fd == VIRTUAL_FD)
            return 0;
        return g_orig_syscall(sysno, fd, a1, a2);
    }

    /* Generic forward: extract up to six arguments and hand them to the
     * original libc syscall (documented bypass channel of _pure_start). */
    {
        long a[6];
        int i;
        va_start(ap, sysno);
        for (i = 0; i < 6; i++)
            a[i] = va_arg(ap, long);
        va_end(ap);
        return g_orig_syscall(sysno, a[0], a[1], a[2], a[3], a[4], a[5]);
    }
}

int main(void)
{
    /* _pure_start returns the original libc syscall; the documented
     * contract requires storing it for bypassing the capture layer. */
    g_orig_syscall = _pure_start(pure_syscall, 0);
    if (g_orig_syscall == NULL)
        return 1;

    /* open() resolves to purelibc's wrapper and reaches the handler as
     * __NR_openat on AT_FDCWD (aarch64 has no plain __NR_open). */
    int fd = open(VIRTUAL_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd != VIRTUAL_FD)
        return 2;

    const char payload[] = "hello purelibc";
    ssize_t n = write(fd, payload, sizeof(payload) - 1);
    if (n != (ssize_t)(sizeof(payload) - 1))
        return 3;
    if (close(fd) != 0)
        return 4;

    if (g_write_calls != 1)
        return 5;
    if (g_backing_len != sizeof(payload) - 1)
        return 6;
    if (strcmp(g_backing, payload) != 0)
        return 7;

    return 0;
}
