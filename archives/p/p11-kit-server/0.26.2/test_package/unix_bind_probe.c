#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int main(void)
{
    struct sockaddr_un address;
    char path[sizeof(address.sun_path)];
    const char *tmpdir;
    int descriptor;
    int result;

    tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        fputs("TMPDIR must identify the socket-capable test directory\n", stderr);
        return 1;
    }

    result = snprintf(path, sizeof(path), "%s/p11srv-bind-%ld.sock", tmpdir,
                      (long)getpid());
    if (result < 0 || (size_t)result >= sizeof(path)) {
        fputs("AF_UNIX probe path generation failed\n", stderr);
        return 1;
    }

    descriptor = socket(AF_UNIX, SOCK_STREAM, 0);
    if (descriptor < 0) {
        perror("AF_UNIX socket");
        return 1;
    }

    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, path, (size_t)result + 1);
    unlink(path);

    if (bind(descriptor, (const struct sockaddr *)&address, sizeof(address)) != 0) {
        result = errno;
        close(descriptor);
        unlink(path);
        fprintf(stderr, "AF_UNIX bind failed: errno=%d (%s)\n", result,
                strerror(result));
        return 1;
    }

    close(descriptor);
    unlink(path);
    printf("filesystem AF_UNIX bind is available in TMPDIR=%s\n", tmpdir);
    return 0;
}
