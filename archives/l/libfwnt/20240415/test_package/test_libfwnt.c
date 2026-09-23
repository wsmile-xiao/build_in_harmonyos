#include <libfwnt.h>

#include <stdint.h>
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
    uint8_t byte_stream[1] = { 0 };
    int result;
    int assertions = 0;
    libfwnt_error_t *error = NULL;
    libfwnt_security_descriptor_t *security_descriptor = NULL;

    version = libfwnt_get_version();
    if (!check(version != NULL, "libfwnt_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240415") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    result = libfwnt_security_descriptor_initialize(
        &security_descriptor,
        &error);
    if (!check(
            result == 1 && security_descriptor != NULL && error == NULL,
            "security_descriptor_initialize failed"))
    {
        libfwnt_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfwnt_security_descriptor_copy_from_byte_stream(
        security_descriptor,
        byte_stream,
        0,
        LIBFWNT_ENDIAN_LITTLE,
        &error);
    if (!check(
            result == -1 && error != NULL,
            "security_descriptor_copy_from_byte_stream error path failed"))
    {
        libfwnt_error_free(&error);
        libfwnt_security_descriptor_free(&security_descriptor, NULL);
        return 1;
    }
    assertions++;
    libfwnt_error_free(&error);

    result = libfwnt_security_descriptor_free(
        &security_descriptor,
        &error);
    if (!check(
            result == 1 && security_descriptor == NULL && error == NULL,
            "security_descriptor_free failed"))
    {
        libfwnt_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfwnt 20240415 consumer test: %d assertions passed\n", assertions);
    return 0;
}
