/* Appended to upstream utils.c: anonymous seekable FILE in a caller-writable
 * directory. Do not interpose libc or redirect another application's files. */
#include <fcntl.h>

FILE *yafc_tmpfile(void)
{
    const char *directory = getenv("TMPDIR");
    char *path = NULL;
    FILE *stream;
    int descriptor, error;
    if(!directory || !*directory)
        directory = gvWorkingDirectory;
    if(!directory || directory[0] != '/') {
        errno = EINVAL;
        return NULL;
    }
    if(asprintf(&path, "%s/yafc-tmp-XXXXXX", directory) < 0) {
        errno = ENOMEM;
        return NULL;
    }
    descriptor = mkstemp(path);
    if(descriptor < 0) {
        error = errno;
        free(path);
        errno = error;
        return NULL;
    }
    if(fcntl(descriptor, F_SETFD, FD_CLOEXEC) < 0 || unlink(path) < 0) {
        error = errno;
        close(descriptor);
        unlink(path);  /* only our exclusive, random, created leaf */
        free(path);
        errno = error;
        return NULL;
    }
    free(path);
    stream = fdopen(descriptor, "w+b");
    if(!stream) {
        error = errno;
        close(descriptor);
        errno = error;
    }
    return stream;
}
