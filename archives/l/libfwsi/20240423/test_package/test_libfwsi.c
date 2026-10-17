#include <libfwsi.h>

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
    libfwsi_error_t *error = NULL;
    libfwsi_item_list_t *item_list = NULL;

    version = libfwsi_get_version();
    if (!check(version != NULL, "libfwsi_get_version returned NULL"))
    {
        return 1;
    }
    assertions++;
    if (!check(strcmp(version, "20240423") == 0, "version mismatch"))
    {
        return 1;
    }
    assertions++;

    result = libfwsi_item_list_initialize(&item_list, &error);
    if (!check(
            result == 1 && item_list != NULL && error == NULL,
            "item_list_initialize failed"))
    {
        libfwsi_error_free(&error);
        return 1;
    }
    assertions++;

    result = libfwsi_item_list_copy_from_byte_stream(
        item_list,
        byte_stream,
        0,
        LIBFWSI_CODEPAGE_WINDOWS_1252,
        &error);
    if (!check(
            result == -1 && error != NULL,
            "item_list_copy_from_byte_stream error path failed"))
    {
        libfwsi_error_free(&error);
        libfwsi_item_list_free(&item_list, NULL);
        return 1;
    }
    assertions++;
    libfwsi_error_free(&error);

    result = libfwsi_item_list_free(&item_list, &error);
    if (!check(
            result == 1 && item_list == NULL && error == NULL,
            "item_list_free failed"))
    {
        libfwsi_error_free(&error);
        return 1;
    }
    assertions++;

    printf("libfwsi 20240423 consumer test: %d assertions passed\n", assertions);
    return 0;
}
