#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

FILE *tmpfile(void)
{
    const char *root = getenv("TMPDIR");
    const char suffix[] = "/pycairo-cairo-XXXXXX";
    char *path;
    FILE *stream;
    size_t length;
    int fd;
    int saved_errno;

    if (root == NULL || root[0] == '\0')
        root = "/data/storage/el2/base/cache";

    length = strlen(root) + sizeof(suffix);
    path = malloc(length);
    if (path == NULL)
        return NULL;

    if (snprintf(path, length, "%s%s", root, suffix) < 0) {
        free(path);
        errno = EIO;
        return NULL;
    }

    fd = mkstemp(path);
    if (fd < 0) {
        free(path);
        return NULL;
    }

    if (unlink(path) != 0) {
        saved_errno = errno;
        close(fd);
        free(path);
        errno = saved_errno;
        return NULL;
    }
    free(path);

    if (fcntl(fd, F_SETFD, FD_CLOEXEC) != 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return NULL;
    }

    stream = fdopen(fd, "w+b");
    if (stream == NULL) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
    }
    return stream;
}
