#define _GNU_SOURCE
#define _XOPEN_SOURCE 700
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

extern char **environ;

static const char *const graalvm_ohos_python_candidates[] = {
    "/data/app/bin/python3.12",
    "/data/app/bin/python3",
    "/data/service/hnp/bin/python3.12",
    "/data/service/hnp/bin/python3",
    "/storage/Users/currentUser/usr/local/bin/python3.12",
    "/storage/Users/currentUser/usr/local/bin/python3",
    NULL,
};

struct selected_python {
    const char *path;
    int descriptor;
};

static const char *path_basename(const char *path)
{
    const char *slash = strrchr(path, '/');
    return slash == NULL ? path : slash + 1;
}

static void close_selected_python(struct selected_python *python)
{
    if (python->descriptor >= 0) {
        close(python->descriptor);
        python->descriptor = -1;
    }
}

static int same_status_identity(const struct stat *left, const struct stat *right)
{
    return left->st_dev == right->st_dev
        && left->st_ino == right->st_ino
        && left->st_size == right->st_size
        && left->st_mtime == right->st_mtime
        && left->st_ctime == right->st_ctime
        && left->st_mode == right->st_mode
        && left->st_uid == right->st_uid
        && left->st_gid == right->st_gid
        && left->st_nlink == right->st_nlink;
}

static int launcher_directory(char *directory, size_t size, const char *launcher)
{
    size_t length = strlen(launcher);
    if (length == 0 || length >= size) {
        return -1;
    }
    memcpy(directory, launcher, length + 1);

    char *slash = strrchr(directory, '/');
    if (slash == NULL) {
        if (size < 2) {
            return -1;
        }
        strcpy(directory, ".");
        return 0;
    }
    if (slash == directory) {
        slash[1] = '\0';
    } else {
        *slash = '\0';
    }
    return 0;
}

static int run_clang_launcher(int argc, char **argv, const char *launcher)
{
    char temporary[PATH_MAX];
    if (launcher_directory(temporary, sizeof(temporary), launcher) != 0) {
        fputs("graalvm ohos-clang cannot derive its temporary directory\n", stderr);
        return 126;
    }
    if (setenv("TMPDIR", temporary, 1) != 0
            || setenv("TMPPREFIX", temporary, 1) != 0) {
        fprintf(
            stderr,
            "graalvm ohos-clang cannot set compiler temporary directory: %s\n",
            strerror(errno)
        );
        return 126;
    }

    const char *clang = "/data/service/hnp/bin/clang";
    if (access(clang, X_OK) != 0) {
        fprintf(
            stderr,
            "graalvm ohos-clang cannot execute %s: %s\n",
            clang,
            strerror(errno)
        );
        return errno == ENOENT ? 127 : 126;
    }

    char **clang_argv = calloc((size_t)argc + 1, sizeof(*clang_argv));
    if (clang_argv == NULL) {
        fputs("graalvm ohos-clang cannot allocate compiler arguments\n", stderr);
        return 126;
    }
    clang_argv[0] = (char *)clang;
    for (int index = 1; index < argc; ++index) {
        clang_argv[index] = argv[index];
    }

    execv(clang, clang_argv);
    int error = errno;
    free(clang_argv);
    fprintf(
        stderr,
        "graalvm ohos-clang cannot execute %s: %s\n",
        clang,
        strerror(error)
    );
    return error == ENOENT ? 127 : 126;
}

static int open_elf_executable(
    const char *candidate,
    struct selected_python *python
)
{
    struct stat path_status;
    if (stat(candidate, &path_status) != 0 || !S_ISREG(path_status.st_mode)
            || access(candidate, X_OK) != 0) {
        return 0;
    }

    int descriptor = open(candidate, O_RDONLY);
    if (descriptor < 0) {
        return 0;
    }

    struct stat open_status;
    if (fstat(descriptor, &open_status) != 0
            || !same_status_identity(&path_status, &open_status)) {
        close(descriptor);
        return 0;
    }

    unsigned char magic[4];
    ssize_t bytes = read(descriptor, magic, sizeof(magic));
    struct stat after_status;
    if (fstat(descriptor, &after_status) != 0
            || !same_status_identity(&open_status, &after_status)
            || bytes != (ssize_t)sizeof(magic)
            || magic[0] != 0x7f
            || magic[1] != 'E'
            || magic[2] != 'L'
            || magic[3] != 'F') {
        close(descriptor);
        return 0;
    }

    if (fcntl(descriptor, F_SETFD, FD_CLOEXEC) != 0) {
        close(descriptor);
        return 0;
    }

    python->path = candidate;
    python->descriptor = descriptor;
    return 1;
}

static int select_python(struct selected_python *python)
{
    python->path = NULL;
    python->descriptor = -1;
    for (size_t index = 0; graalvm_ohos_python_candidates[index] != NULL;
         ++index) {
        const char *candidate = graalvm_ohos_python_candidates[index];
        if (open_elf_executable(candidate, python)) {
            return 0;
        }
    }
    return -1;
}

static int resolve_self(char *resolved, size_t size, const char *argv0)
{
    if (size < 2) {
        return -1;
    }
    ssize_t length = readlink("/proc/self/exe", resolved, size - 1);
    if (length >= 0 && (size_t)length < size - 1) {
        resolved[length] = '\0';
        return 0;
    }

    if (argv0 == NULL || argv0[0] == '\0') {
        return -1;
    }
    if (strchr(argv0, '/') != NULL) {
        return realpath(argv0, resolved) == NULL ? -1 : 0;
    }

    const char *cursor = getenv("PATH");
    if (cursor == NULL) {
        return -1;
    }
    for (;;) {
        const char *separator = strchr(cursor, ':');
        size_t directory_length = separator == NULL
            ? strlen(cursor)
            : (size_t)(separator - cursor);
        int written;
        if (directory_length == 0) {
            written = snprintf(resolved, size, "./%s", argv0);
        } else {
            written = snprintf(
                resolved,
                size,
                "%.*s/%s",
                (int)directory_length,
                cursor,
                argv0
            );
        }
        if (written > 0 && (size_t)written < size
                && access(resolved, X_OK) == 0) {
            char canonical[PATH_MAX];
            if (realpath(resolved, canonical) != NULL) {
                if (strlen(canonical) >= size) {
                    return -1;
                }
                strcpy(resolved, canonical);
                return 0;
            }
        }
        if (separator == NULL) {
            break;
        }
        cursor = separator + 1;
    }
    return -1;
}

int main(int argc, char **argv)
{
    char launcher[PATH_MAX];
    if (resolve_self(launcher, sizeof(launcher), argv[0]) != 0) {
        fputs("graalvm native-image cannot resolve its launcher path\n", stderr);
        return 126;
    }
    if (strcmp(path_basename(launcher), "ohos-clang") == 0) {
        return run_clang_launcher(argc, argv, launcher);
    }

    char companion[PATH_MAX];
    int written = snprintf(companion, sizeof(companion), "%s.py", launcher);
    if (written <= 0 || (size_t)written >= sizeof(companion)) {
        fputs("graalvm native-image companion path is too long\n", stderr);
        return 126;
    }
    struct stat companion_status;
    if (lstat(companion, &companion_status) != 0
            || !S_ISREG(companion_status.st_mode)) {
        fprintf(
            stderr,
            "graalvm native-image Python companion is missing: %s\n",
            companion
        );
        return 126;
    }

    struct selected_python python;
    if (select_python(&python) != 0) {
        fputs("graalvm native-image cannot find a trusted Python runtime\n", stderr);
        return 127;
    }

    char **python_argv = calloc((size_t)argc + 3, sizeof(*python_argv));
    if (python_argv == NULL) {
        close_selected_python(&python);
        fputs("graalvm native-image cannot allocate launcher arguments\n", stderr);
        return 126;
    }
    unsetenv("PYTHONHOME");
    unsetenv("PYTHONPATH");
    unsetenv("LD_LIBRARY_PATH");
    python_argv[0] = (char *)python.path;
    python_argv[1] = (char *)"-I";
    python_argv[2] = companion;
    for (int index = 1; index < argc; ++index) {
        python_argv[index + 2] = argv[index];
    }

    fexecve(python.descriptor, python_argv, environ);
    int error = errno;
    close_selected_python(&python);
    free(python_argv);
    fprintf(
        stderr,
        "graalvm native-image cannot execute %s: %s\n",
        python.path,
        strerror(error)
    );
    return error == ENOENT ? 127 : 126;
}
