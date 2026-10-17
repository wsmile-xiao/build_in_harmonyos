#include <libphdi.h>

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
    libphdi_error_t *error = NULL;
    libphdi_handle_t *object = NULL;

    version = libphdi_get_version();
    if (!check(version != NULL, "libphdi_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240508") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            libphdi_get_access_flags_read() == LIBPHDI_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libphdi_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libphdi_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;
    libphdi_error_free(&error);

    result = libphdi_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libphdi_check_file_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libphdi_check_file_signature error path failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;
    libphdi_error_free(&error);

    result = libphdi_handle_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libphdi_handle_initialize failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libphdi_handle_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libphdi_handle_free failed"))
    {
        libphdi_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libphdi 20240508 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
