#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <mpi.h>

#ifndef O_BINARY
#define O_BINARY 0
#endif

static int parse_environment_int(const char *name, int minimum, int maximum)
{
    const char *value = getenv(name);
    char *endptr;
    long parsed;

    if (value == NULL || value[0] == '\0') {
        return -1;
    }
    errno = 0;
    parsed = strtol(value, &endptr, 10);
    if (errno == ERANGE || endptr == value || *endptr != '\0' ||
        parsed < minimum || parsed > maximum) {
        return -1;
    }
    return (int) parsed;
}

static int write_all_bytes(int fd, const char *data, size_t length)
{
    size_t offset = 0;

    while (offset < length) {
        ssize_t written = write(fd, data + offset, length - offset);
        if (written > 0) {
            offset += (size_t) written;
            continue;
        }
        if (written < 0 && errno == EINTR) {
            continue;
        }
        return -1;
    }
    return 0;
}

static int append_file_line(const char *path, const char *text)
{
    int fd;
    int saved_errno = 0;
    int rc = 0;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) {
        return -1;
    }
    if (write_all_bytes(fd, text, strlen(text)) != 0) {
        saved_errno = errno;
        rc = -1;
    }
    if (close(fd) != 0 && rc == 0) {
        saved_errno = errno;
        rc = -1;
    }
    if (rc != 0) {
        errno = saved_errno;
    }
    return rc;
}

static int write_file_once(const char *path, const char *text)
{
    int fd;
    int saved_errno = 0;
    int rc = 0;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) {
        return -1;
    }
    if (write_all_bytes(fd, text, strlen(text)) != 0) {
        saved_errno = errno;
        rc = -1;
    }
    if (close(fd) != 0 && rc == 0) {
        saved_errno = errno;
        rc = -1;
    }
    if (rc != 0) {
        errno = saved_errno;
    }
    return rc;
}

static int append_record_env(const char *env_name, const char *role, int rank)
{
    const char *path = getenv(env_name);
    char line[128];
    int length;
    long process_group = (long) getpgid(0);

    length = snprintf(line, sizeof(line), "role=%s rank=%d pid=%ld pgid=%ld\n",
                      role, rank, (long) getpid(), process_group);
    if (length <= 0 || length >= (int) sizeof(line)) {
        return -1;
    }
    return append_file_line(path, line);
}

static int write_canary_env(const char *env_name, const char *role, int rank)
{
    return append_record_env(env_name, role, rank);
}

static int write_armed_marker(const char *mode)
{
    const char *path = getenv("CODEX_MPI_FRAME_ARMED_FILE");
    char marker[64];
    int length;

    length = snprintf(marker, sizeof(marker), "%s\n", mode);
    if (length <= 0 || length >= (int) sizeof(marker)) {
        return -1;
    }
    return write_file_once(path, marker);
}

static int is_lower_hex_token(const char *token)
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

static int observer_release_state(const char *path, const char *token)
{
    char actual[66];
    char expected[66];
    int expected_length;
    int fd;
    size_t offset = 0;

    if (path == NULL || path[0] == '\0' || !is_lower_hex_token(token)) {
        return -1;
    }
    expected_length = snprintf(expected, sizeof(expected), "%s\n", token);
    if (expected_length != 65) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_BINARY);
    if (fd < 0) {
        return errno == ENOENT ? 1 : -1;
    }
    while (offset < sizeof(actual)) {
        ssize_t count = read(fd, actual + offset, sizeof(actual) - offset);
        if (count > 0) {
            offset += (size_t) count;
            continue;
        }
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            close(fd);
            return -1;
        }
        break;
    }
    if (close(fd) != 0) {
        return -1;
    }
    return offset == (size_t) expected_length &&
        memcmp(actual, expected, (size_t) expected_length) == 0 ? 0 : 1;
}

static int wait_for_observer_release(void)
{
    const char *path = getenv("CODEX_MPI_OBSERVER_RELEASE_FILE");
    const char *token = getenv("CODEX_MPI_OBSERVER_RELEASE_TOKEN");
    struct timespec delay = {0, 100000000L};
    int attempt;

    for (attempt = 0; attempt < 100; attempt++) {
        int state = observer_release_state(path, token);
        if (state == 0) {
            return 0;
        }
        if (state < 0) {
            return -1;
        }
        while (nanosleep(&delay, &delay) != 0) {
            if (errno != EINTR) {
                return -1;
            }
        }
        delay.tv_sec = 0;
        delay.tv_nsec = 100000000L;
    }
    return -1;
}

static int is_valid_mode(const char *mode)
{
    return strcmp(mode, "valid-int-max") == 0 ||
           strcmp(mode, "valid-int-min") == 0;
}

static int parse_mode(int argc, char **argv, const char **mode)
{
    static const char spawned_prefix[] = "--spawned=";
    const size_t prefix_length = sizeof(spawned_prefix) - 1;
    const char *argument;

    if (argc == 2) {
        argument = argv[1];
    } else if (argc == 1 &&
               strncmp(argv[0], spawned_prefix, prefix_length) == 0) {
        argument = argv[0];
    } else {
        return -1;
    }
    if (strncmp(argument, spawned_prefix, prefix_length) == 0) {
        if (argument[prefix_length] == '\0') {
            return -1;
        }
        *mode = argument + prefix_length;
        return 1;
    }
    *mode = argument;
    return 0;
}

static int build_spawned_argument(char *buffer, size_t capacity, const char *mode)
{
    int length = snprintf(buffer, capacity, "--spawned=%s", mode);

    return length > 0 && (size_t) length < capacity ? 0 : -1;
}

static const char *abort_frame(const char *mode)
{
    if (strcmp(mode, "missing") == 0) {
        return "cmd=abort message=missing-exitcode\n";
    }
    if (strcmp(mode, "nonnumeric") == 0) {
        return "cmd=abort exitcode=not-a-number message=invalid-exitcode\n";
    }
    if (strcmp(mode, "empty") == 0) {
        return "cmd=abort exitcode= message=empty-exitcode\n";
    }
    if (strcmp(mode, "overflow") == 0) {
        return "cmd=abort exitcode=999999999999999999999999999999 "
               "message=overflow-exitcode\n";
    }
    if (strcmp(mode, "trailing-junk") == 0) {
        return "cmd=abort exitcode=1x message=trailing-junk\n";
    }
    if (strcmp(mode, "above-int") == 0) {
        return "cmd=abort exitcode=2147483648 message=above-int\n";
    }
    if (strcmp(mode, "below-int") == 0) {
        return "cmd=abort exitcode=-2147483649 message=below-int\n";
    }
    if (strcmp(mode, "leading-tab") == 0) {
        return "cmd=abort exitcode=\t1 message=leading-tab\n";
    }
    if (strcmp(mode, "leading-cr") == 0) {
        return "cmd=abort exitcode=\r1 message=leading-cr\n";
    }
    if (strcmp(mode, "leading-vt") == 0) {
        return "cmd=abort exitcode=\v1 message=leading-vt\n";
    }
    if (strcmp(mode, "leading-ff") == 0) {
        return "cmd=abort exitcode=\f1 message=leading-ff\n";
    }
    if (strcmp(mode, "valid-int-max") == 0) {
        return "cmd=abort exitcode=2147483647 message=valid-int-max\n";
    }
    if (strcmp(mode, "valid-int-min") == 0) {
        return "cmd=abort exitcode=-2147483648 message=valid-int-min\n";
    }
    return NULL;
}

int main(int argc, char **argv)
{
    char spawned_argument[64];
    /* MPI_Comm_spawn receives command separately; this payload contains arguments only. */
    char *spawn_arguments[] = {spawned_argument, NULL};
    const char *frame;
    const char *mode = NULL;
    MPI_Comm parent;
    MPI_Comm spawned;
    int child_process;
    int pmi_fd;
    int rank;
    int size;

    child_process = parse_mode(argc, argv, &mode);
    if (child_process < 0 || signal(SIGPIPE, SIG_IGN) == SIG_ERR) {
        return 151;
    }
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS ||
        MPI_Comm_get_parent(&parent) != MPI_SUCCESS) {
        return 152;
    }

    if (parent != MPI_COMM_NULL) {
        if (child_process != 1 ||
            MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
            MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS ||
            size != 1 ||
            rank != 0 ||
            append_record_env("CODEX_MPI_PID_FILE", "spawned", 0) != 0) {
            return 153;
        }
        if (wait_for_observer_release() != 0) {
            return 155;
        }
        if (is_valid_mode(mode)) {
            if (MPI_Barrier(parent) != MPI_SUCCESS) {
                return 154;
            }
            sleep(4);
            if (write_canary_env("CODEX_MPI_VALID_CANARY", "spawned", 0) != 0) {
                return 154;
            }
            sleep(120);
            return 163;
        }
        sleep(4);
        if (write_canary_env("CODEX_MPI_MALFORMED_CANARY", "spawned", 0) != 0) {
            return 155;
        }
        sleep(120);
        return 156;
    }

    frame = abort_frame(mode);
    pmi_fd = parse_environment_int("PMI_FD", 3, INT_MAX);
    if (frame == NULL ||
        build_spawned_argument(spawned_argument, sizeof(spawned_argument), mode) != 0 ||
        pmi_fd < 0 ||
        MPI_Comm_rank(MPI_COMM_WORLD, &rank) != MPI_SUCCESS ||
        MPI_Comm_size(MPI_COMM_WORLD, &size) != MPI_SUCCESS || size != 2 ||
        append_record_env("CODEX_MPI_PID_FILE", "parent", rank) != 0) {
        return 157;
    }
    if (MPI_Comm_set_errhandler(MPI_COMM_WORLD, MPI_ERRORS_RETURN) != MPI_SUCCESS ||
        MPI_Comm_spawn(argv[0], spawn_arguments, 1, MPI_INFO_NULL, 0, MPI_COMM_WORLD,
                       &spawned, MPI_ERRCODES_IGNORE) != MPI_SUCCESS) {
        return 158;
    }

    if (wait_for_observer_release() != 0) {
        return 159;
    }

    if (rank == 0) {
        if (write_armed_marker(mode) != 0 ||
            write_all_bytes(pmi_fd, frame, strlen(frame)) != 0) {
            return 159;
        }
    }

    if (is_valid_mode(mode)) {
        if (MPI_Barrier(spawned) != MPI_SUCCESS ||
            MPI_Barrier(MPI_COMM_WORLD) != MPI_SUCCESS) {
            return 160;
        }
        sleep(4);
        if (write_canary_env("CODEX_MPI_VALID_CANARY", "parent", rank) != 0) {
            return 160;
        }
        sleep(120);
        return 163;
    }

    sleep(4);
    if (rank == 1 &&
        write_canary_env("CODEX_MPI_MALFORMED_CANARY", "parent", rank) != 0) {
        return 161;
    }
    sleep(120);
    return 162;
}
