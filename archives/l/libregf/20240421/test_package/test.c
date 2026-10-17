#include <libregf.h>

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
    const char *version = libregf_get_version();
    check(version != NULL && version[0] != '\0', "libregf_get_version");

    check(libregf_get_access_flags_read() != 0, "libregf_get_access_flags_read");

    libregf_file_t *file = NULL;
    libregf_error_t *error = NULL;
    int result = libregf_file_initialize(&file, &error);
    check(result == 1 && file != NULL, "libregf_file_initialize");
    if (error != NULL) {
        libregf_error_free(&error);
        error = NULL;
    }

    FILE *tmp = fopen("test_package_input.txt", "w");
    if (tmp != NULL) {
        fputs("libregf test_package probe, not a REGF file.\n", tmp);
        fclose(tmp);
    }
    result = libregf_check_file_signature("test_package_input.txt", &error);
    check(result == 0, "libregf_check_file_signature rejects non-REGF");
    if (error != NULL) {
        libregf_error_free(&error);
        error = NULL;
    }
    remove("test_package_input.txt");

    if (file != NULL) {
        result = libregf_file_free(&file, &error);
        check(result == 1 && file == NULL, "libregf_file_free");
        if (error != NULL) {
            libregf_error_free(&error);
            error = NULL;
        }
    } else {
        check(0, "libregf_file_free");
    }

    printf("RESULT: %d/%d\n", passed, total);
    return passed == total ? 0 : 1;
}
