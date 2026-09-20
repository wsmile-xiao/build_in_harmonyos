/* Generic consumer test for libfsapfs 20240429.
 *
 * Links against the installed package (not the in-tree build) and exercises
 * the public API surface a downstream consumer depends on: version identity,
 * access flags, codepage get/set including the error path, the container and
 * volume signature check error paths, and the container lifecycle.
 */
#include <libfsapfs.h>

#include <stdio.h>
#include <string.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *version;
    int codepage = 0;
    int result;
    int assertions = 0;
    libfsapfs_error_t *error = NULL;
    libfsapfs_container_t *container = NULL;

    version = libfsapfs_get_version();
    if (!check(version != NULL, "libfsapfs_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240429") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libfsapfs_get_access_flags_read() == LIBFSAPFS_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfsapfs_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsapfs_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsapfs_error_free(&error);

    result = libfsapfs_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsapfs_check_container_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_container_signature error path failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsapfs_error_free(&error);

    result = libfsapfs_check_volume_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature error path failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsapfs_error_free(&error);

    result = libfsapfs_container_initialize(&container, &error);
    if (!check(
            result == 1 && container != NULL && error == NULL,
            "container_initialize failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsapfs_container_free(&container, &error);
    if (!check(
            result == 1 && container == NULL && error == NULL,
            "container_free failed")) {
        libfsapfs_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfsapfs 20240429 consumer test: %d assertions passed\n", assertions);
    return 0;
}
