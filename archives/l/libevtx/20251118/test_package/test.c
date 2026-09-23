#include <libevtx.h>

#include <stdio.h>

static int total = 0;
static int passed = 0;

static void check(int ok, const char *name)
{
    total++;
    if (ok) {
        passed++;
        printf("case %d: %s: PASS\n", total, name);
    } else {
        printf("case %d: %s: FAIL\n", total, name);
    }
}

int main(void)
{
    const char *version = libevtx_get_version();
    check(version != NULL && version[0] != '\0', "libevtx_get_version");

    check(libevtx_get_access_flags_read() != 0, "libevtx_get_access_flags_read");

    libevtx_file_t *file = NULL;
    libevtx_error_t *error = NULL;
    int result = libevtx_file_initialize(&file, &error);
    check(result == 1 && file != NULL, "libevtx_file_initialize");
    if (error != NULL) {
        libevtx_error_free(&error);
        error = NULL;
    }

    FILE *tmp = fopen("test_package_input.txt", "w");
    if (tmp != NULL) {
        fputs("libevtx test_package probe, not an EVTX file.\n", tmp);
        fclose(tmp);
    }
    result = libevtx_check_file_signature("test_package_input.txt", &error);
    check(result == 0, "libevtx_check_file_signature rejects non-EVTX");
    if (error != NULL) {
        libevtx_error_free(&error);
        error = NULL;
    }
    remove("test_package_input.txt");

    if (file != NULL) {
        result = libevtx_file_free(&file, &error);
        check(result == 1 && file == NULL, "libevtx_file_free");
        if (error != NULL) {
            libevtx_error_free(&error);
            error = NULL;
        }
    } else {
        check(0, "libevtx_file_free");
    }

    printf("RESULT: %d/%d\n", passed, total);
    return passed == total ? 0 : 1;
}
