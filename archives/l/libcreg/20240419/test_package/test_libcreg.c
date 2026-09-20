#include <libcreg.h>

#include <stdio.h>
#include <string.h>

static int check(int condition, const char *message)
{
    if (!condition)
    {
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
    libcreg_error_t *error = NULL;
    libcreg_file_t *object = NULL;

    version = libcreg_get_version();
    if (!check(version != NULL, "libcreg_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240419") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            libcreg_get_access_flags_read() == LIBCREG_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libcreg_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;

    result = libcreg_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;
    libcreg_error_free(&error);

    result = libcreg_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;

    result = libcreg_check_file_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libcreg_check_file_signature error path failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;
    libcreg_error_free(&error);

    result = libcreg_file_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libcreg_file_initialize failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;

    result = libcreg_file_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libcreg_file_free failed"))
    {
        libcreg_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libcreg 20240419 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
