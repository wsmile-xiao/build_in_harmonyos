#include <editorconfig/editorconfig.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message)                                                \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "check failed: %s\n", message);                    \
            return 1;                                                            \
        }                                                                        \
    } while (0)

#define CHECK_CLEANUP(condition, message)                                        \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "check failed: %s\n", message);                    \
            status = 1;                                                          \
            goto cleanup;                                                        \
        }                                                                        \
    } while (0)

static int test_version(void)
{
    const char *suffix;
    int major = -1;
    int minor = -1;
    int patch = -1;

    editorconfig_get_version(&major, &minor, &patch);
    CHECK(major == 0, "library major version");
    CHECK(minor == 12, "library minor version");
    CHECK(patch == 9, "library patch version");
    suffix = editorconfig_get_version_suffix();
    CHECK(suffix != NULL, "version suffix pointer");
    CHECK(strcmp(suffix, "") == 0,
          "stable release version suffix");
    return 0;
}

static int test_handle_version(void)
{
    editorconfig_handle handle = editorconfig_handle_init();
    int major = -1;
    int minor = -1;
    int patch = -1;
    int status = 0;

    CHECK(handle != NULL, "handle initialization");
    editorconfig_handle_set_version(handle, 1, 2, 3);
    editorconfig_handle_get_version(handle, &major, &minor, &patch);
    CHECK_CLEANUP(major == 1, "handle major version");
    CHECK_CLEANUP(minor == 2, "handle minor version");
    CHECK_CLEANUP(patch == 3, "handle patch version");

    editorconfig_handle_set_version(handle, -1, 7, -1);
    editorconfig_handle_get_version(handle, &major, &minor, &patch);
    CHECK_CLEANUP(major == 1, "negative major preserves value");
    CHECK_CLEANUP(minor == 7, "non-negative minor updates value");
    CHECK_CLEANUP(patch == 3, "negative patch preserves value");

cleanup:
    if (editorconfig_handle_destroy(handle) != 0) {
        fprintf(stderr, "check failed: handle destruction\n");
        status = 1;
    }
    return status;
}

static int test_conf_filename(void)
{
    const char *filename;
    editorconfig_handle handle = editorconfig_handle_init();
    int status = 0;

    CHECK(handle != NULL, "handle initialization");
    CHECK_CLEANUP(editorconfig_handle_get_name_value_count(handle) == 0,
                  "new handle property count");
    CHECK_CLEANUP(editorconfig_handle_get_err_file(handle) == NULL,
                  "new handle error file");
    editorconfig_handle_set_conf_file_name(handle, ".custom-editorconfig");
    filename = editorconfig_handle_get_conf_file_name(handle);
    CHECK_CLEANUP(filename != NULL, "custom config filename pointer");
    CHECK_CLEANUP(strcmp(filename, ".custom-editorconfig") == 0,
                  "custom config filename value");

cleanup:
    if (editorconfig_handle_destroy(handle) != 0) {
        fprintf(stderr, "check failed: handle destruction\n");
        status = 1;
    }
    return status;
}

static int test_relative_path_error(void)
{
    const char *message;
    int result;
    editorconfig_handle handle = editorconfig_handle_init();
    int status = 0;

    CHECK(handle != NULL, "handle initialization");
    result = editorconfig_parse("relative-file.c", handle);
    CHECK_CLEANUP(result == EDITORCONFIG_PARSE_NOT_FULL_PATH,
                  "relative path error code");
    message = editorconfig_get_error_msg(result);
    CHECK_CLEANUP(message != NULL, "relative path error message pointer");
    CHECK_CLEANUP(message[0] != '\0', "relative path error message value");
    CHECK_CLEANUP(editorconfig_handle_get_err_file(handle) == NULL,
                  "relative path has no parser error file");

cleanup:
    if (editorconfig_handle_destroy(handle) != 0) {
        fprintf(stderr, "check failed: handle destruction\n");
        status = 1;
    }
    return status;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr,
                "usage: %s version|handle_version|conf_filename|relative_path_error\n",
                argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "version") == 0)
        return test_version();
    if (strcmp(argv[1], "handle_version") == 0)
        return test_handle_version();
    if (strcmp(argv[1], "conf_filename") == 0)
        return test_conf_filename();
    if (strcmp(argv[1], "relative_path_error") == 0)
        return test_relative_path_error();
    fprintf(stderr, "unknown test case: %s\n", argv[1]);
    return 2;
}
