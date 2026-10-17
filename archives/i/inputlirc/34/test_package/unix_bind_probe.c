/* Consumer probe: it does not link inputlirc (the package ships a daemon, not a
 * library), it reproduces exactly the socket setup inputlircd performs in
 * add_unixsocket() so the platform verdict is measured, not read off a log. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>
#include <stddef.h>
#include <sys/socket.h>
#include <sys/un.h>

static int fs_bind(const char *path) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); return -1; }
    struct sockaddr_un sa;
    memset(&sa, 0, sizeof sa);
    sa.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof sa.sun_path) { close(fd); return -1; }
    strcpy(sa.sun_path, path);
    unlink(path);
    socklen_t len = offsetof(struct sockaddr_un, sun_path) + strlen(path) + 1;
    int rc = bind(fd, (struct sockaddr *)&sa, len);
    int e = errno;
    if (rc == 0) printf("fs-bind %s: OK (unexpected here)\n", path);
    else printf("fs-bind %s: FAIL errno=%d(%s)\n", path, e, strerror(e));
    close(fd);
    return rc == 0 ? 0 : e;
}

static int abstract_bind(const char *name) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un sa;
    memset(&sa, 0, sizeof sa);
    sa.sun_family = AF_UNIX;
    sa.sun_path[0] = '\0';
    strcpy(sa.sun_path + 1, name);
    socklen_t len = offsetof(struct sockaddr_un, sun_path) + 1 + strlen(name);
    int rc = bind(fd, (struct sockaddr *)&sa, len);
    int e = errno;
    if (rc == 0) printf("abstract-bind @%s: OK\n", name);
    else printf("abstract-bind @%s: FAIL errno=%d(%s)\n", name, e, strerror(e));
    close(fd);
    return rc == 0 ? 0 : e;
}

int main(int argc, char **argv) {
    const char *dir = argc > 1 ? argv[1] : ".";
    char path[512];
    snprintf(path, sizeof path, "%s/il34-probe.sock", dir);
    int fs = fs_bind(path);
    int ab = abstract_bind("il34-probe");
    /* Documented OHOS behaviour: a filesystem AF_UNIX endpoint cannot be created
     * (EPERM, the same errno mkfifo gets in the same directory) while the
     * abstract namespace still binds. Anything else flips this test red. */
    if (fs == EPERM && ab == 0) {
        printf("VERDICT: filesystem unix-socket bind refused, abstract namespace works\n");
        return 0;
    }
    printf("VERDICT: CHANGED from documented behaviour (fs=%d abstract=%d)\n", fs, ab);
    return 1;
}
