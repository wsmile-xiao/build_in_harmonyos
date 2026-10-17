#include <libolecf.h>

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
    libolecf_error_t *error = NULL;
    libolecf_file_t *object = NULL;

    version = libolecf_get_version();
    if (!check(version != NULL, "libolecf_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240427") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    result = libolecf_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libolecf_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;
    libolecf_error_free(&error);

    result = libolecf_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libolecf_check_file_signature(NULL, &error);
    if (!check(result == -1 && error != NULL, "libolecf_check_file_signature error path failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;
    libolecf_error_free(&error);

    result = libolecf_file_initialize(&object, &error);
    if (!check(
            result == 1 && object != NULL && error == NULL,
            "libolecf_file_initialize failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;

    result = libolecf_file_free(&object, &error);
    if (!check(
            result == 1 && object == NULL && error == NULL,
            "libolecf_file_free failed"))
    {
        libolecf_error_free(&error);
        return 1;
    }
    assertions++;

    printf(
        "libolecf 20240427 consumer test: %d assertions passed\n",
        assertions);
    return 0;
}
