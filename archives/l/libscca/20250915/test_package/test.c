#include <libscca.h>

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
    const char *version = libscca_get_version();
    check(version != NULL && version[0] != '\0', "libscca_get_version");

    check(libscca_get_access_flags_read() != 0, "libscca_get_access_flags_read");

    libscca_file_t *file = NULL;
    libscca_error_t *error = NULL;
    int result = libscca_file_initialize(&file, &error);
    check(result == 1 && file != NULL, "libscca_file_initialize");
    if (error != NULL) {
        libscca_error_free(&error);
        error = NULL;
    }

    FILE *tmp = fopen("test_package_input.txt", "w");
    if (tmp != NULL) {
        fputs("libscca test_package probe, not a Prefetch file.\n", tmp);
        fclose(tmp);
    }
    result = libscca_check_file_signature("test_package_input.txt", &error);
    check(result == 0, "libscca_check_file_signature rejects non-Prefetch");
    if (error != NULL) {
        libscca_error_free(&error);
        error = NULL;
    }
    remove("test_package_input.txt");

    if (file != NULL) {
        result = libscca_file_free(&file, &error);
        check(result == 1 && file == NULL, "libscca_file_free");
        if (error != NULL) {
            libscca_error_free(&error);
            error = NULL;
        }
    } else {
        check(0, "libscca_file_free");
    }

    printf("RESULT: %d/%d\n", passed, total);
    return passed == total ? 0 : 1;
}
