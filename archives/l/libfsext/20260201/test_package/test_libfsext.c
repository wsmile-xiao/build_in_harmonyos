#include <libfsext.h>

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
    libfsext_error_t *error = NULL;
    libfsext_volume_t *object = NULL;

    version = libfsext_get_version();
    if (!check(version != NULL, "libfsext_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20260201") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            libfsext_get_access_flags_read() == LIBFSEXT_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfsext_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsext_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;
    libfsext_error_free(&error);

    result = libfsext_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsext_check_volume_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libfsext_check_volume_signature error path failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;
    libfsext_error_free(&error);

    result = libfsext_volume_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libfsext_volume_initialize failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfsext_volume_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libfsext_volume_free failed"))
    {
        libfsext_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libfsext 20260201 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
