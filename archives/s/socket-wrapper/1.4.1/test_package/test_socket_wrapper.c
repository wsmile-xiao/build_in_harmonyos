#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#include <socket_wrapper.h>

static int wrapper_dir_has_socket_file(const char *dir)
{
    DIR *stream = opendir(dir);
    struct dirent *entry;

    if (stream == NULL) {
        return 0;
    }

    while ((entry = readdir(stream)) != NULL) {
        if (entry->d_name[0] == 'T' || entry->d_name[0] == 'U') {
            closedir(stream);
            return 1;
        }
    }

    closedir(stream);
    return 0;
}

static int fail_with_errno(const char *operation)
{
    fprintf(stderr, "%s failed: errno=%d (%s)\n",
            operation, errno, strerror(errno));
    return 1;
}

int main(void)
{
    static const char payload[] = "swrap-ohos";
    const char *dir = getenv("SOCKET_WRAPPER_DIR");
    const char *iface = getenv("SOCKET_WRAPPER_IFACE");
    struct sockaddr_in address;
    struct sockaddr_in peer;
    struct stat directory_stat;
    socklen_t peer_length = sizeof(peer);
    char buffer[sizeof(payload)] = {0};
    int server = -1;
    int client = -1;
    int accepted = -1;
    ssize_t received;

    if (dir == NULL || dir[0] == '\0') {
        fputs("SOCKET_WRAPPER_DIR must be set\n", stderr);
        return 1;
    }
    if (iface == NULL || iface[0] == '\0') {
        fputs("SOCKET_WRAPPER_IFACE must be set\n", stderr);
        return 1;
    }
    if (stat(dir, &directory_stat) != 0 ||
        !S_ISDIR(directory_stat.st_mode)) {
        fprintf(stderr, "SOCKET_WRAPPER_DIR is not a directory: %s\n", dir);
        return 1;
    }
    if (socket_wrapper_enabled() != 1) {
        fputs("socket_wrapper_enabled() did not observe LD_PRELOAD\n", stderr);
        return 1;
    }

    server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) {
        return fail_with_errno("server socket");
    }

    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(21777);
    address.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(server, (struct sockaddr *)&address, sizeof(address)) != 0) {
        return fail_with_errno("bind");
    }
    if (listen(server, 1) != 0) {
        return fail_with_errno("listen");
    }

    client = socket(AF_INET, SOCK_STREAM, 0);
    if (client < 0) {
        return fail_with_errno("client socket");
    }
    if (connect(client, (struct sockaddr *)&address, sizeof(address)) != 0) {
        return fail_with_errno("connect");
    }
    if (send(client, payload, sizeof(payload) - 1, 0) !=
        (ssize_t)(sizeof(payload) - 1)) {
        return fail_with_errno("send");
    }

    accepted = accept(server, (struct sockaddr *)&peer, &peer_length);
    if (accepted < 0) {
        return fail_with_errno("accept");
    }
    if (peer.sin_family != AF_INET ||
        peer.sin_addr.s_addr != inet_addr("127.0.0.1")) {
        fprintf(stderr, "unexpected peer family=%u address=%s\n",
                peer.sin_family, inet_ntoa(peer.sin_addr));
        return 1;
    }

    received = recv(accepted, buffer, sizeof(buffer), 0);
    if (received != (ssize_t)(sizeof(payload) - 1) ||
        memcmp(buffer, payload, sizeof(payload) - 1) != 0) {
        fprintf(stderr, "payload mismatch: received=%zd errno=%d\n",
                received, errno);
        return 1;
    }

    close(accepted);
    close(client);
    if (!wrapper_dir_has_socket_file(dir)) {
        fprintf(stderr, "no socket_wrapper socket file found in %s\n", dir);
        return 1;
    }
    close(server);

    printf("socket-wrapper redirected IPv4 loopback through AF_UNIX in %s\n",
           dir);
    puts("socket-wrapper LD_PRELOAD consumer test passed");
    return 0;
}
