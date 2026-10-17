/* Small C launcher for the upstream Cython test command. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char *python = getenv("CBINDGEN_CYTHON_PYTHON");
    const char *script = getenv("CBINDGEN_CYTHON_SCRIPT");
    if (!python || !script) {
        fputs("Cython test interpreter/script are required\n", stderr);
        return 2;
    }
    char **args = calloc((size_t)argc + 2, sizeof(*args));
    if (!args) {
        perror("calloc");
        return 2;
    }
    args[0] = (char *)python;
    args[1] = (char *)script;
    for (int i = 1; i < argc; ++i)
        args[i + 1] = argv[i];
    execv(python, args);
    perror("execv Cython");
    free(args);
    return 127;
}
