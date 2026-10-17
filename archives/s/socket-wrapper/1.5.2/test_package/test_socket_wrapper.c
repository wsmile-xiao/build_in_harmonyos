#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef SOCKET_WRAPPER_TEST_LIBRARY
#error "SOCKET_WRAPPER_TEST_LIBRARY is not defined"
#endif

static int wrapper_dir_has_socket_file(const char *dir)
{
    DIR *d = opendir(dir);
    struct dirent *ent;

    if (d == NULL) {
        return 0;
    }
    while ((ent = readdir(d)) != NULL) {
        /* socket_wrapper names its unix sockets after the interface and
         * port, e.g. 'T021641' for a TCP socket. Look for any of the
         * TCP ('T') or UDP ('U') socket file prefixes. */
        if (ent->d_name[0] == 'T' || ent->d_name[0] == 'U') {
            closedir(d);
            return 1;
        }
    }
    closedir(d);
    return 0;
}

int main(void)
{
    const char *dir = getenv("SOCKET_WRAPPER_DIR");
    const char *iface = getenv("SOCKET_WRAPPER_IFACE");
    struct sockaddr_in addr;
    struct sockaddr_in peer;
    struct stat st;
    socklen_t plen;
    int srv = -1;
    int cli = -1;
    int acc = -1;
    ssize_t n;
    char buf[64];
    int rc;

    if (dir == NULL || dir[0] == '\0') {
        fprintf(stderr, "SOCKET_WRAPPER_DIR must be set\n");
        return 1;
    }
    if (iface == NULL || iface[0] == '\0') {
        fprintf(stderr, "SOCKET_WRAPPER_IFACE must be set\n");
        return 1;
    }
    if (stat(dir, &st) != 0 || !S_ISDIR(st.st_mode)) {
        fprintf(stderr, "SOCKET_WRAPPER_DIR is not a directory: %s\n", dir);
        return 1;
    }

    srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv < 0) {
        perror("socket");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(21777);
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }
    if (listen(srv, 1) < 0) {
        perror("listen");
        return 1;
    }

    cli = socket(AF_INET, SOCK_STREAM, 0);
    if (cli < 0) {
        perror("socket cli");
        return 1;
    }
    if (connect(cli, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect");
        return 1;
    }

    rc = send(cli, "swrap-ohos", 10, 0);
    if (rc != 10) {
        fprintf(stderr, "send rc=%d errno=%d\n", rc, errno);
        return 1;
    }

    plen = sizeof(peer);
    acc = accept(srv, (struct sockaddr *)&peer, &plen);
    if (acc < 0) {
        perror("accept");
        return 1;
    }
    /* socket_wrapper converts the AF_UNIX peer back to a real
     * AF_INET loopback address on accept. */
    if (peer.sin_family != AF_INET ||
        ntohl(peer.sin_addr.s_addr) != ntohl(inet_addr("127.0.0.1"))) {
        fprintf(stderr,
                "unexpected peer family=%u addr=%s\n",
                peer.sin_family,
                inet_ntoa(peer.sin_addr));
        return 1;
    }

    n = recv(acc, buf, sizeof(buf) - 1, 0);
    if (n != 10 || memcmp(buf, "swrap-ohos", 10) != 0) {
        fprintf(stderr, "recv n=%zd errno=%d\n", n, errno);
        return 1;
    }
    buf[n] = '\0';

    close(acc);
    acc = -1;
    close(cli);
    cli = -1;

    /* The wrapper must have created a 'T<iface><port>' AF_UNIX socket
     * file inside SOCKET_WRAPPER_DIR to prove the redirection happened. */
    if (!wrapper_dir_has_socket_file(dir)) {
        fprintf(stderr,
                "no socket_wrapper socket file found in %s\n",
                dir);
        return 1;
    }

    printf("socket-wrapper redirected AF_INET 127.0.0.1:21777 to AF_UNIX in %s (payload=%s)\n",
           dir, buf);
    puts("socket-wrapper LD_PRELOAD loopback redirection check passed");
    return 0;
}
