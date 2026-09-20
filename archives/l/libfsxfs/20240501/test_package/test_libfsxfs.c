/* Generic consumer test for libfsxfs 20240501.
 *
 * Links against the installed package (not the in-tree build) and exercises
 * the public API surface a downstream consumer depends on: version identity,
 * access flags, codepage get/set including the error path, the volume
 * signature check error path, and the volume lifecycle.
 */
#include <libfsxfs.h>

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
    libfsxfs_error_t *error = NULL;
    libfsxfs_volume_t *volume = NULL;

    version = libfsxfs_get_version();
    if (!check(version != NULL, "libfsxfs_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240501") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libfsxfs_get_access_flags_read() == LIBFSXFS_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfsxfs_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsxfs_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsxfs_error_free(&error);

    result = libfsxfs_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsxfs_check_volume_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature error path failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsxfs_error_free(&error);

    result = libfsxfs_volume_initialize(&volume, &error);
    if (!check(
            result == 1 && volume != NULL && error == NULL,
            "volume_initialize failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsxfs_volume_free(&volume, &error);
    if (!check(
            result == 1 && volume == NULL && error == NULL,
            "volume_free failed")) {
        libfsxfs_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfsxfs 20240501 consumer test: %d assertions passed\n", assertions);
    return 0;
}
