/* Generic consumer test for libpff 20231205.
 *
 * Links against the installed package (not the in-tree build) and exercises
 * the public API surface a downstream consumer depends on: version identity,
 * access flags, codepage get/set including the error path, the PFF file
 * signature check error path, and the file object lifecycle including a
 * failed open.
 */
#include <libpff.h>

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
    libpff_error_t *error = NULL;
    libpff_file_t *file = NULL;

    version = libpff_get_version();
    if (!check(version != NULL, "libpff_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20231205") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libpff_get_access_flags_read() == LIBPFF_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libpff_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;

    result = libpff_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;
    libpff_error_free(&error);

    result = libpff_set_codepage(LIBPFF_CODEPAGE_WINDOWS_1252, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;
    libpff_error_free(&error);

    result = libpff_check_file_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_file_signature error path failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;
    libpff_error_free(&error);

    result = libpff_file_initialize(&file, &error);
    if (!check(
            result == 1 && file != NULL && error == NULL,
            "file_initialize failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;

    result = libpff_file_open(file, "/nonexistent/libpff-ohos.pst", LIBPFF_OPEN_READ, &error);
    if (!check(
            result == -1 && error != NULL,
            "file_open on a missing file must fail")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;
    libpff_error_free(&error);

    result = libpff_file_free(&file, &error);
    if (!check(
            result == 1 && file == NULL && error == NULL,
            "file_free failed")) {
        libpff_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libpff 20231205 consumer test: %d assertions passed\n", assertions);
    return 0;
}
