#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int is_supported_script(const char *name)
{
    return strcmp(name, "djlink") == 0 || strcmp(name, "djstrip") == 0 ||
           strcmp(name, "djelfextract") == 0;
}

int main(int argc, char **argv)
{
    static const char bash[] = "/data/service/hnp/bin/bash";
    static const char hnp_bin[] = "/data/service/hnp/bin";
    char executable[PATH_MAX];
    char script[PATH_MAX];
    char **bash_argv;
    char *launcher_path;
    char *separator;
    const char *path;
    const char *name;
    size_t launcher_path_size;
    ssize_t length;
    int index;

    length = readlink("/proc/self/exe", executable, sizeof(executable) - 1);
    if (length < 0 || (size_t)length >= sizeof(executable) - 1) {
        perror("djstub launcher: readlink");
        return 126;
    }
    executable[length] = '\0';

    separator = strrchr(executable, '/');
    if (separator == NULL) {
        fputs("djstub launcher: invalid executable path\n", stderr);
        return 126;
    }
    *separator = '\0';

    name = strrchr(argv[0], '/');
    name = name == NULL ? argv[0] : name + 1;
    if (!is_supported_script(name)) {
        fprintf(stderr, "djstub launcher: unsupported command: %s\n", name);
        return 126;
    }

    if (snprintf(script, sizeof(script), "%s/../libexec/djstub/%s", executable,
                 name) >= (int)sizeof(script)) {
        fputs("djstub launcher: script path is too long\n", stderr);
        return 126;
    }

    path = getenv("PATH");
    launcher_path_size = sizeof(hnp_bin) + (path == NULL ? 0 : strlen(path) + 1);
    launcher_path = malloc(launcher_path_size);
    if (launcher_path == NULL) {
        perror("djstub launcher: malloc");
        return 126;
    }
    if (path == NULL || *path == '\0') {
        snprintf(launcher_path, launcher_path_size, "%s", hnp_bin);
    } else {
        snprintf(launcher_path, launcher_path_size, "%s:%s", hnp_bin, path);
    }
    if (setenv("PATH", launcher_path, 1) != 0) {
        perror("djstub launcher: setenv");
        free(launcher_path);
        return 126;
    }
    free(launcher_path);

    bash_argv = calloc((size_t)argc + 2, sizeof(*bash_argv));
    if (bash_argv == NULL) {
        perror("djstub launcher: calloc");
        return 126;
    }
    bash_argv[0] = (char *)bash;
    bash_argv[1] = script;
    for (index = 1; index < argc; ++index) {
        bash_argv[index + 1] = argv[index];
    }

    execv(bash, bash_argv);
    fprintf(stderr, "djstub launcher: cannot execute %s: %s\n", bash,
            strerror(errno));
    free(bash_argv);
    return 126;
}
