#include <errno.h>
#include <pthread.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#include <spnav.h>

struct server_state {
    int listener;
    int ok;
};

static void *serve(void *argument)
{
    struct server_state *state = (struct server_state *)argument;
    struct pollfd ready = {state->listener, POLLIN, 0};
    struct timeval timeout = {5, 0};
    int client;
    int32_t request = 0;
    int32_t response = 1; /* Protocol version 1. */
    if (poll(&ready, 1, 5000) != 1 || !(ready.revents & POLLIN)) {
        fprintf(stderr, "consumer peer: listener did not become ready\n");
        return NULL;
    }
    client = accept(state->listener, NULL, NULL);
    if (client < 0) {
        perror("consumer peer: accept");
        return NULL;
    }
    if (setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) ||
        setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout))) {
        perror("consumer peer: socket timeout");
        close(client);
        return NULL;
    }
    if (read(client, &request, sizeof(request)) == sizeof(request) &&
        (request & 0xffff0000) == 0x7faa0000 &&
        send(client, &response, sizeof(response), MSG_NOSIGNAL) == sizeof(response))
        state->ok = 1;
    else
        fprintf(stderr, "consumer peer: invalid or incomplete protocol handshake\n");
    close(client);
    return NULL;
}

int main(void)
{
    struct sockaddr_un address;
    struct server_state state = {-1, 0};
    pthread_t thread;
    char path[sizeof(address.sun_path)];
    char directory[sizeof(address.sun_path)];
    const char *temporary_root = getenv("TMPDIR");
    int thread_started = 0;
    int client_open = 0;
    int socket_bound = 0;
    int result = 1;

    if (spnav_fd() != -1 || spnav_close() != -1) {
        fprintf(stderr, "consumer: unexpected initial library state\n");
        return 1;
    }
    if (!temporary_root || !*temporary_root)
        temporary_root = "/tmp";
    /* A unique directory on a socket-capable native filesystem is both short
     * enough for sun_path and independent of the HMDFS Conan build tree. */
    if (snprintf(directory, sizeof(directory), "%s/spnav-XXXXXX", temporary_root) >=
        (int)sizeof(directory) - 2) {
        fprintf(stderr, "consumer: TMPDIR socket path too long\n");
        return 2;
    }
    if (!mkdtemp(directory)) {
        perror("consumer: private temporary directory");
        return 2;
    }
    snprintf(path, sizeof(path), "%s/s", directory);
    state.listener = socket(AF_UNIX, SOCK_STREAM, 0);
    if (state.listener < 0) {
        perror("consumer: socket");
        result = 3;
        goto done;
    }
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    strcpy(address.sun_path, path);
    if (bind(state.listener, (struct sockaddr *)&address, sizeof(address))) {
        perror("consumer: bind");
        goto done;
    }
    socket_bound = 1;
    if (listen(state.listener, 1)) {
        perror("consumer: listen");
        goto done;
    }
    {
        int thread_error = pthread_create(&thread, NULL, serve, &state);
        if (thread_error) {
            fprintf(stderr, "consumer: pthread_create: %s\n", strerror(thread_error));
            goto done;
        }
    }
    thread_started = 1;
    if (setenv("SPNAV_SOCKET", path, 1) || spnav_open() != 0) {
        perror("consumer: spnav_open");
        goto done;
    }
    client_open = 1;
    if (spnav_fd() < 0 || spnav_protocol() != 1) {
        fprintf(stderr, "consumer: invalid connected protocol state\n");
        goto done;
    }
    result = 0;
done:
    if (client_open && (spnav_close() != 0 || spnav_fd() != -1))
        result = 4;
    if (thread_started)
        pthread_join(thread, NULL);
    if (result == 0 && !state.ok)
        result = 5;
    if (state.listener >= 0)
        close(state.listener);
    if (socket_bound)
        unlink(path);
    if (rmdir(directory) && result == 0) {
        perror("consumer: temporary directory cleanup");
        result = 6;
    }
    if (result == 0)
        puts("libspnav AF_UNIX consumer handshake PASS");
    return result;
}
