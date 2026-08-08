/* tmpfile-shim.c — OHOS libc tmpfile() compatibility shim.
 *
 * Root cause (audit 20260801): OHOS libc tmpfile() ignores TMPDIR and
 * attempts the system temp dir (/data/local/tmp), which returns EACCES(13).
 * libctf ctf_link_write (ctf-link.c:1981) calls tmpfile() to stage CTF
 * compressed output; on OHOS this fails with "Cannot link: Permission denied"
 * (libctf-writable/ctf-compressed FAIL). No test expectation changes, no
 * upstream source changes: this shim restores POSIX tmpfile() semantics
 * (anonymous temp file, removed on close) using mkstemp in TMPDIR.
 *
 * Review fixes (20260802):
 *  - TMPDIR unset/empty -> fall back to "." (cwd, writable in testsuite)
 *    instead of a hard-coded absolute path.
 *  - Detect snprintf truncation (path too long) and fail cleanly.
 *  - Set FD_CLOEXEC on the fd (POSIX 2024 / glibc behaviour).
 *  - close(fd) if fdopen() fails (no fd leak).
 *  - Report unlink() failure instead of silently ignoring it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>

FILE *tmpfile(void) {
    const char *d = getenv("TMPDIR");
    if (!d || !*d)
        d = ".";
    char tmpl[512];
    int n = snprintf(tmpl, sizeof(tmpl), "%s/ctftmpXXXXXX", d);
    if (n < 0 || n >= (int)sizeof(tmpl)) {
        fprintf(stderr, "tmpfile-shim: TMPDIR path too long\n");
        errno = ENAMETOOLONG;
        return NULL;
    }
    int fd = mkstemp(tmpl);
    if (fd < 0) {
        fprintf(stderr, "tmpfile-shim: mkstemp failed in %s: %s\n",
                d, strerror(errno));
        return NULL;
    }
    /* POSIX 2024 / glibc: temp files are close-on-exec. */
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    if (unlink(tmpl) < 0) {
        fprintf(stderr, "tmpfile-shim: unlink %s failed: %s\n",
                tmpl, strerror(errno));
        close(fd);
        return NULL;
    }
    FILE *f = fdopen(fd, "w+b");
    if (!f) {
        fprintf(stderr, "tmpfile-shim: fdopen failed: %s\n", strerror(errno));
        close(fd);
        return NULL;
    }
    return f;
}
