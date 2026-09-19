/*
 * test.c — libgtop-tools installed-package smoke test.
 *
 * Verifies that libgtop_daemon2 and libgtop_server2 binaries are present
 * and executable in the Conan package directory. Returns 0 on success.
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

static int check_binary(const char *path, const char *name)
{
    struct stat st;
    if (stat(path, &st) != 0) {
        fprintf(stderr, "FAIL: %s not found at %s\n", name, path);
        return 1;
    }
    if (!(st.st_mode & S_IXUSR) && !(st.st_mode & S_IXGRP) && !(st.st_mode & S_IXOTH)) {
        fprintf(stderr, "FAIL: %s at %s is not executable\n", name, path);
        return 1;
    }
    printf("OK: %s found at %s\n", name, path);
    return 0;
}

int main(int argc, char *argv[])
{
    int result = 0;

    if (argc < 3) {
        fprintf(stderr, "Usage: %s <libgtop_daemon2_path> <libgtop_server2_path>\n", argv[0]);
        return 1;
    }

    result |= check_binary(argv[1], "libgtop_daemon2");
    result |= check_binary(argv[2], "libgtop_server2");

    if (result == 0) {
        puts("libgtop-tools smoke test passed");
    }
    return result;
}
