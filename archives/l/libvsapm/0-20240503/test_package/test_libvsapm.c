#include <libvsapm.h>

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
    libvsapm_error_t *error = NULL;
    libvsapm_volume_t *object = NULL;

    version = libvsapm_get_version();
    if (!check(version != NULL, "libvsapm_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240503") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            libvsapm_get_access_flags_read() == LIBVSAPM_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libvsapm_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvsapm_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;
    libvsapm_error_free(&error);

    result = libvsapm_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvsapm_check_volume_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libvsapm_check_volume_signature error path failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;
    libvsapm_error_free(&error);

    result = libvsapm_volume_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libvsapm_volume_initialize failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;

    result = libvsapm_volume_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libvsapm_volume_free failed"))
    {
        libvsapm_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libvsapm 20240503 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
