#include <assuan.h>
#include <gpg-error.h>

#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static gpg_error_t echo_handler(assuan_context_t ctx, char *line) {
    return assuan_send_data(ctx, line, strlen(line));
}

struct response_buffer {
    char data[64];
    size_t length;
};

static gpg_error_t collect_data(void *opaque, const void *buffer, size_t length) {
    struct response_buffer *output = opaque;

    if (!buffer) {
        return 0;
    }
    if (length > sizeof(output->data) - output->length - 1) {
        return gpg_error(GPG_ERR_TOO_LARGE);
    }
    memcpy(output->data + output->length, buffer, length);
    output->length += length;
    output->data[output->length] = '\0';
    return 0;
}

static int run_server(int fd) {
    assuan_context_t ctx = NULL;
    gpg_error_t err;
    int context_owns_fd = 0;

    err = assuan_new(&ctx);
    if (!err) {
        assuan_fd_t assuan_fd = assuan_fd_from_posix_fd(fd);
        err = assuan_init_socket_server(ctx, assuan_fd, ASSUAN_SOCKET_SERVER_ACCEPTED);
        context_owns_fd = !err;
    }
    if (!err) {
        err = assuan_register_command(ctx, "ECHO", echo_handler, NULL);
    }
    if (!err) {
        err = assuan_accept(ctx);
    }
    if (!err) {
        err = assuan_process(ctx);
    }

    assuan_release(ctx);
    if (!context_owns_fd) {
        close(fd);
    }
    return err ? 1 : 0;
}

int main(void) {
    const char *version;
    assuan_context_t ctx = NULL;
    gpg_error_t err;
    int sockets[2];
    pid_t child;
    int status;
    struct response_buffer response = {{0}, 0};
    int context_owns_fd = 0;

    alarm(30);
    signal(SIGPIPE, SIG_IGN);
    version = assuan_check_version("3.0.2");
    if (!version || strcmp(version, "3.0.2") < 0) {
        fprintf(stderr, "unexpected libassuan version: %s\n", version ? version : "null");
        return 1;
    }
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0) {
        perror("socketpair");
        return 2;
    }

    child = fork();
    if (child < 0) {
        perror("fork");
        close(sockets[0]);
        close(sockets[1]);
        return 3;
    }
    if (child == 0) {
        close(sockets[0]);
        _exit(run_server(sockets[1]));
    }

    close(sockets[1]);
    err = assuan_new(&ctx);
    if (!err) {
        context_owns_fd = 1;
        err = assuan_socket_connect_fd(ctx, assuan_fd_from_posix_fd(sockets[0]), 0);
    }
    if (!err) {
        err = assuan_transact(
            ctx, "ECHO OpenHarmony", collect_data, &response, NULL, NULL, NULL, NULL
        );
    }
    if (!err && strcmp(response.data, "OpenHarmony") != 0) {
        err = gpg_error(GPG_ERR_BAD_DATA);
    }
    if (!err) {
        err = assuan_transact(ctx, "BYE", NULL, NULL, NULL, NULL, NULL, NULL);
    }

    assuan_release(ctx);
    if (!context_owns_fd) {
        close(sockets[0]);
    }
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status)) {
        fprintf(stderr, "libassuan server failed\n");
        return 4;
    }
    if (err) {
        fprintf(stderr, "libassuan transaction failed: %s\n", gpg_strerror(err));
        return 5;
    }

    alarm(0);
    puts("libassuan client/server transaction passed");
    return 0;
}
