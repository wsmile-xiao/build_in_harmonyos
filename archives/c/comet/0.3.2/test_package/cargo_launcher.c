/* Explicitly exec the runtime helper; OHOS Rust cannot launch Python shebangs.
 * Same proven scheme as archives/c/cbindgen/0.28.0/test_package/cargo_launcher.c. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char *python = getenv("COMET_RUNTIME_PYTHON");
    const char *helper = getenv("COMET_RUNTIME_HELPER");
    if (!python || !*python || !helper || !*helper) {
        fputs("Activate the comet Conan environment before using Rust tools.\n", stderr);
        return 2;
    }
    char **args = calloc((size_t)argc + 3, sizeof(*args));
    if (!args) {
        perror("Rust runtime arguments");
        return 2;
    }
    args[0] = (char *)python;
    args[1] = (char *)helper;
    const char *name = strrchr(argv[0], '/');
    name = name ? name + 1 : argv[0];
    args[2] = strcmp(name, "rustc-launcher") == 0 ? "rustc" : "cargo";
    for (int i = 1; i < argc; ++i)
        args[i + 2] = argv[i];
    execv(python, args);
    perror("Rust runtime helper");
    free(args);
    return 127;
}
