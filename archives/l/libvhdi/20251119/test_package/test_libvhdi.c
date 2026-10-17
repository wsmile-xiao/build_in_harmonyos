#include <libvhdi.h>

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
    libvhdi_error_t *error = NULL;
    libvhdi_file_t *file = NULL;

    version = libvhdi_get_version();
    if (!check(version != NULL, "libvhdi_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20251119") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libvhdi_get_access_flags_read() == LIBVHDI_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libvhdi_get_access_flags_write() == LIBVHDI_ACCESS_FLAG_WRITE,
            "write access flag mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libvhdi_get_access_flags_read_write()
                == (LIBVHDI_ACCESS_FLAG_READ | LIBVHDI_ACCESS_FLAG_WRITE),
            "read/write access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libvhdi_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvhdi_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;
    libvhdi_error_free(&error);

    result = libvhdi_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvhdi_check_file_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_file_signature error path failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;
    libvhdi_error_free(&error);

    result = libvhdi_file_initialize(&file, &error);
    if (!check(
            result == 1 && file != NULL && error == NULL,
            "file_initialize failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvhdi_file_free(&file, &error);
    if (!check(
            result == 1 && file == NULL && error == NULL,
            "file_free failed")) {
        libvhdi_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libvhdi 20251119 consumer test: %d assertions passed\n", assertions);
    return 0;
}
