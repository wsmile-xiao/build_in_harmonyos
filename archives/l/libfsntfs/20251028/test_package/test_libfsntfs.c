#include <libfsntfs.h>

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
    libfsntfs_error_t *error = NULL;
    libfsntfs_volume_t *volume = NULL;

    version = libfsntfs_get_version();
    if (!check(version != NULL, "libfsntfs_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20251028") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libfsntfs_get_access_flags_read() == LIBFSNTFS_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfsntfs_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsntfs_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsntfs_error_free(&error);

    result = libfsntfs_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsntfs_check_volume_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature error path failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;
    libfsntfs_error_free(&error);

    result = libfsntfs_volume_initialize(&volume, &error);
    if (!check(
            result == 1 && volume != NULL && error == NULL,
            "volume_initialize failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsntfs_volume_free(&volume, &error);
    if (!check(
            result == 1 && volume == NULL && error == NULL,
            "volume_free failed")) {
        libfsntfs_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfsntfs 20251028 consumer test: %d assertions passed\n", assertions);
    return 0;
}
