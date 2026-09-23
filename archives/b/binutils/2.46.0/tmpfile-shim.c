/* Test-only tmpfile compatibility shim for OHOS HMDFS environments. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int binutils_tmpfile_shim_active(void)
{
    return 1;
}

FILE *tmpfile(void)
{
    const char *directory = getenv("TMPDIR");
    char template_path[512];
    FILE *stream;
    int fd;

    if (directory == NULL || *directory == '\0')
        directory = ".";
    if (snprintf(template_path, sizeof(template_path),
                 "%s/binutils-tmpfile-XXXXXX", directory) >=
        (int)sizeof(template_path)) {
        errno = ENAMETOOLONG;
        return NULL;
    }
    fd = mkstemp(template_path);
    if (fd < 0)
        return NULL;
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    if (unlink(template_path) < 0) {
        close(fd);
        return NULL;
    }
    stream = fdopen(fd, "w+b");
    if (stream == NULL)
        close(fd);
    return stream;
}
