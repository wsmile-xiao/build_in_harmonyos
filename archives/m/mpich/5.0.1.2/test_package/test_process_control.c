#define _POSIX_C_SOURCE 200809L

#include <mpi.h>

#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int record_pid(void)
{
    const char *path = getenv("CODEX_MPI_PID_FILE");
    char line[64];
    int fd;
    int length;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) {
        return -1;
    }
    length = snprintf(line, sizeof(line), "%ld\n", (long)getpid());
    if (length <= 0 || length >= (int)sizeof(line) ||
        write(fd, line, (size_t)length) != length) {
        close(fd);
        return -1;
    }
    return close(fd);
}

static int write_pid_file(const char *variable)
{
    const char *path = getenv(variable);
    char line[64];
    int fd;
    int length;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) {
        return -1;
    }
    length = snprintf(line, sizeof(line), "%ld\n", (long)getpid());
    if (length <= 0 || length >= (int)sizeof(line) ||
        write(fd, line, (size_t)length) != length) {
        close(fd);
        return -1;
    }
    return close(fd);
}

static int write_escape_canary(void)
{
    const char *path = getenv("CODEX_MPI_ESCAPE_CANARY");
    const char marker[] = "escaped\n";
    int fd;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) {
        return -1;
    }
    if (write(fd, marker, sizeof(marker) - 1) != (ssize_t)(sizeof(marker) - 1)) {
        close(fd);
        return -1;
    }
    return close(fd);
}

static int valid_release_token(const char *token)
{
    size_t index;

    if (token == NULL || strlen(token) != 64) {
        return 0;
    }
    for (index = 0; index < 64; index++) {
        if (!((token[index] >= '0' && token[index] <= '9') ||
              (token[index] >= 'a' && token[index] <= 'f'))) {
            return 0;
        }
    }
    return 1;
}

static int write_escape_armed(const char *token)
{
    const char *path = getenv("CODEX_MPI_ESCAPE_ARMED_FILE");
    char record[66];
    int fd;

    if (!valid_release_token(token) || path == NULL || path[0] == '\0') {
        return -1;
    }
    memcpy(record, token, 64);
    record[64] = '\n';
    record[65] = '\0';
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) {
        return -1;
    }
    if (write(fd, record, 65) != 65) {
        close(fd);
        return -1;
    }
    return close(fd);
}

static int wait_for_escape_release(const char *token)
{
    const char *path = getenv("CODEX_MPI_ESCAPE_RELEASE_FILE");
    const struct timespec delay = {0, 10 * 1000 * 1000};
    char record[66];
    int attempt;

    if (!valid_release_token(token) || path == NULL || path[0] == '\0') {
        return -1;
    }
    for (attempt = 0; attempt < 12000; attempt++) {
        int fd = open(path, O_RDONLY);
        if (fd >= 0) {
            ssize_t length = read(fd, record, sizeof(record));
            close(fd);
            if (length == 65 && memcmp(record, token, 64) == 0 &&
                record[64] == '\n') {
                return 0;
            }
        }
        nanosleep(&delay, NULL);
    }
    return -1;
}

static int start_detached_descendant(int ignore_term)
{
    const char *release_token = getenv("CODEX_MPI_ESCAPE_RELEASE_TOKEN");
    int ready_pipe[2];
    int status;
    char ready;
    pid_t child;
    pid_t grandchild;

    if (pipe(ready_pipe) != 0) {
        return -1;
    }
    child = fork();
    if (child < 0) {
        close(ready_pipe[0]);
        close(ready_pipe[1]);
        return -1;
    }
    if (child == 0) {
        close(ready_pipe[0]);
        if (setsid() < 0) {
            _exit(141);
        }
        grandchild = fork();
        if (grandchild < 0) {
            _exit(142);
        }
        if (grandchild > 0) {
            _exit(0);
        }
        if (!valid_release_token(release_token) ||
            (ignore_term && signal(SIGTERM, SIG_IGN) == SIG_ERR) ||
            write_pid_file("CODEX_MPI_ESCAPE_PID_FILE") != 0 ||
            write_escape_armed(release_token) != 0 ||
            write(ready_pipe[1], "R", 1) != 1) {
            _exit(143);
        }
        close(ready_pipe[1]);
        close(STDIN_FILENO);
        close(STDOUT_FILENO);
        close(STDERR_FILENO);
        if (wait_for_escape_release(release_token) != 0 ||
            write_escape_canary() != 0) {
            _exit(144);
        }
        sleep(120);
        _exit(0);
    }

    close(ready_pipe[1]);
    if (read(ready_pipe[0], &ready, 1) != 1 || ready != 'R') {
        close(ready_pipe[0]);
        return -1;
    }
    close(ready_pipe[0]);
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) ||
        WEXITSTATUS(status) != 0) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    int ierr;

    if (argc != 2 || MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        return 131;
    }
    if (MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS || size != 2 ||
        record_pid() != 0) {
        MPI_Abort(MPI_COMM_WORLD, 132);
    }
    if (strcmp(argv[1], "abort") == 0) {
        if (rank == 0) {
            sleep(1);
            MPI_Abort(MPI_COMM_WORLD, 133);
        }
        sleep(120);
        return 134;
    }
    if (strcmp(argv[1], "timeout") == 0) {
        sleep(120);
        return 135;
    }
    if (strcmp(argv[1], "detach") == 0 ||
        strcmp(argv[1], "detach-kill") == 0) {
        if (rank == 0 &&
            start_detached_descendant(strcmp(argv[1], "detach-kill") == 0) != 0) {
            MPI_Abort(MPI_COMM_WORLD, 137);
        }
        if (MPI_Barrier(MPI_COMM_WORLD) != MPI_SUCCESS) {
            MPI_Abort(MPI_COMM_WORLD, 138);
        }
    }
    ierr = MPI_Finalize();
    return ierr == MPI_SUCCESS ? 0 : 136;
}
