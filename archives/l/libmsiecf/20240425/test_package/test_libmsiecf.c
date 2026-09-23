#include <libmsiecf.h>

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
    libmsiecf_error_t *error = NULL;
    libmsiecf_file_t *object = NULL;

    version = libmsiecf_get_version();
    if (!check(version != NULL, "libmsiecf_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240425") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            libmsiecf_get_access_flags_read() == LIBMSIECF_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libmsiecf_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libmsiecf_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;
    libmsiecf_error_free(&error);

    result = libmsiecf_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libmsiecf_check_file_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libmsiecf_check_file_signature error path failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;
    libmsiecf_error_free(&error);

    result = libmsiecf_file_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libmsiecf_file_initialize failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libmsiecf_file_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libmsiecf_file_free failed"))
    {
        libmsiecf_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libmsiecf 20240425 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
