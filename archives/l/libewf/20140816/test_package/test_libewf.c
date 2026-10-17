#include <stdio.h>
#include <string.h>

#include <libewf.h>

#define CHECK(n, cond)                                     \
    do {                                                   \
        if (!(cond)) {                                     \
            fprintf(stderr, "assertion %d failed: %s\n",  \
                    n, #cond);                             \
            return n;                                      \
        }                                                  \
    } while (0)

int main(void)
{
    const char *version;
    libewf_handle_t *handle = NULL;
    libewf_error_t *error = NULL;
    FILE *fixture;
    int signature_result;

    /* 1: the library reports a version string. */
    version = libewf_get_version();
    CHECK(1, version != NULL);

    /* 2: the version matches the adapted upstream release. */
    CHECK(2, strcmp(version, "20140816") == 0);

    /* 3: the read access flag matches the public ABI constant. */
    CHECK(3, libewf_get_access_flags_read() == LIBEWF_ACCESS_FLAG_READ);

    /* 4: a handle can be initialized. */
    CHECK(4, libewf_handle_initialize(&handle, &error) == 1);
    CHECK(4, handle != NULL);

    /* 5: the handle can be freed (and is nulled afterwards). */
    CHECK(5, libewf_handle_free(&handle, &error) == 1);
    CHECK(5, handle == NULL);

    /* 6: a plain-text file is correctly reported as not holding
     * an EWF signature (negative path of the file API). */
    fixture = fopen("libewf_negative_fixture.txt", "w");
    CHECK(6, fixture != NULL);
    CHECK(6, fputs("this is not an Expert Witness image\n", fixture) >= 0);
    CHECK(6, fclose(fixture) == 0);
    signature_result = libewf_check_file_signature(
        "libewf_negative_fixture.txt", &error);
    CHECK(6, signature_result == 0);
    CHECK(6, remove("libewf_negative_fixture.txt") == 0);

    printf("libewf API assertions: 6 passed\n");
    return 0;
}
