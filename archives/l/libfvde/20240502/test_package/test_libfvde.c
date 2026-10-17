/* Consumer test for the libfvde Conan package (generic, non-OHOS specific).
 *
 * Exercises the public API that the packaged library actually exports:
 * version string, read access flags, codepage get/set (success and error
 * path), volume signature check error path and the volume object lifecycle.
 */
#include <libfvde.h>

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
    libfvde_error_t *error = NULL;
    libfvde_volume_t *volume = NULL;

    version = libfvde_get_version();
    if (!check(version != NULL, "libfvde_get_version returned NULL")) {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240502") == 0, "version mismatch")) {
        return 1;
    }
    assertions++;

    if (!check(
            libfvde_get_access_flags_read() == LIBFVDE_ACCESS_FLAG_READ,
            "read access flag mismatch")) {
        return 1;
    }
    assertions++;

    result = libfvde_get_codepage(&codepage, &error);
    if (!check(result == 1 && error == NULL, "get_codepage failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfvde_get_codepage(NULL, &error);
    if (!check(result == -1 && error != NULL, "get_codepage error path failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;
    libfvde_error_free(&error);

    result = libfvde_set_codepage(0, &error);
    if (!check(result == 1 && error == NULL, "set_codepage failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfvde_check_volume_signature(NULL, &error);
    if (!check(
            result == -1 && error != NULL,
            "check_volume_signature error path failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;
    libfvde_error_free(&error);

    libfvde_notify_set_verbose(0);
    result = libfvde_notify_set_stream(stderr, &error);
    if (!check(result == 1 && error == NULL, "notify_set_stream failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;
    /* Returns 0 (not 1) when the stream was supplied by the caller instead of
     * being opened by the library; see libfvde_notify_stream_close() doc. */
    result = libfvde_notify_stream_close(&error);
    if (!check(result == 0 && error == NULL, "notify_stream_close failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfvde_volume_initialize(&volume, &error);
    if (!check(
            result == 1 && volume != NULL && error == NULL,
            "volume_initialize failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfvde_volume_free(&volume, &error);
    if (!check(
            result == 1 && volume == NULL && error == NULL,
            "volume_free failed")) {
        libfvde_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfvde %s consumer test: %d assertions passed\n", version, assertions);
    return 0;
}
