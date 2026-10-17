/* Consumer test for libevt 20240421.
 *
 * Exercises the public libevt API from the installed Conan package:
 * version string, access flags, codepage get/set round trip, error
 * object lifecycle, and EVT file open/close lifecycle (a real EVT
 * binary sample is not bundled, so open() must fail cleanly on a
 * non-EVT file and report a proper error).
 */
#include <libevt.h>

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
    int codepage = -1;
    int result;
    int assertions = 0;
    libevt_error_t *error = NULL;
    libevt_file_t *file = NULL;

    /* 1. version string */
    version = libevt_get_version();
    if (!check(version != NULL, "libevt_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240421") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    /* 2. read access flags */
    if (!check(
            libevt_get_access_flags_read() == LIBEVT_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    /* 3. codepage get (default) */
    result = libevt_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libevt_error_free(&error);
        return 1;
    }
    assertions++;

    /* 4. codepage get error path (NULL argument) */
    result = libevt_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libevt_error_free(&error);
        return 1;
    }
    assertions++;
    libevt_error_free(&error);

    /* 5. codepage set round trip */
    result = libevt_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libevt_error_free(&error);
        return 1;
    }
    assertions++;

    /* 6. file object lifecycle */
    result = libevt_file_initialize(&file, &error);
    if (!check(result == 1 && file != NULL, "file_initialize failed")) {
        libevt_error_free(&error);
        return 1;
    }
    assertions++;

    /* 7. open on a non-EVT file must fail cleanly with an error */
    result = libevt_file_open(file, "/etc/hostname", LIBEVT_OPEN_READ, &error);
    if (!check(
            result == -1 && error != NULL,
            "open on non-EVT file did not fail cleanly")) {
        libevt_file_close(file, NULL);
        libevt_file_free(&file, NULL);
        return 1;
    }
    assertions++;
    libevt_error_free(&error);

    /* 8. close on a file that never opened: libevt semantics is to
     * return -1 with an error set (missing file IO handle) */
    result = libevt_file_close(file, &error);
    if (!check(
            result == -1 && error != NULL,
            "close on never-opened file did not report an error")) {
        libevt_error_free(&error);
        libevt_file_free(&file, NULL);
        return 1;
    }
    assertions++;
    libevt_error_free(&error);

    result = libevt_file_free(&file, &error);
    if (!check(result == 1 && file == NULL, "file_free failed")) {
        libevt_error_free(&error);
        return 1;
    }
    assertions++;

    printf("test_libevt: %d assertions passed\n", assertions);
    return 0;
}
