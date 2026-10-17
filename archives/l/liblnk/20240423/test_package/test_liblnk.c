#include <liblnk.h>

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
    liblnk_error_t *error = NULL;
    liblnk_file_t *object = NULL;

    version = liblnk_get_version();
    if (!check(version != NULL, "liblnk_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240423") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    if (!check(
            liblnk_get_access_flags_read() == LIBLNK_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = liblnk_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;

    result = liblnk_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;
    liblnk_error_free(&error);

    result = liblnk_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;

    result = liblnk_check_file_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "liblnk_check_file_signature error path failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;
    liblnk_error_free(&error);

    result = liblnk_file_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "liblnk_file_initialize failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;

    result = liblnk_file_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "liblnk_file_free failed"))
    {
        liblnk_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "liblnk 20240423 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
