#include <editorconfig/editorconfig.h>

#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define CHECK(condition, message)                                                \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "check failed: %s\n", message);                     \
            return 1;                                                            \
        }                                                                        \
    } while (0)

#define CHECK_CLEANUP(condition, message)                                        \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "check failed: %s\n", message);                     \
            status = 1;                                                          \
            goto cleanup;                                                        \
        }                                                                        \
    } while (0)

static int write_text(const char *path, const char *text)
{
    FILE *stream = fopen(path, "w");

    if (stream == NULL)
        return -1;
    if (fputs(text, stream) == EOF) {
        fclose(stream);
        return -1;
    }
    return fclose(stream);
}

int main(void)
{
    char cwd[PATH_MAX];
    char source_path[PATH_MAX];
    editorconfig_handle handle = NULL;
    int major = 0;
    int minor = 0;
    int patch = 0;
    int count;
    int found_indent_style = 0;
    int found_indent_size = 0;
    int index;
    int path_length;
    int status = 0;

    editorconfig_get_version(&major, &minor, &patch);
    CHECK(major == 0, "major version");
    CHECK(minor == 12, "minor version");
    CHECK(patch == 9, "patch version");

    handle = editorconfig_handle_init();
    CHECK(handle != NULL, "handle initialization");
    CHECK_CLEANUP(
        write_text(".editorconfig",
                   "root = true\n[*]\nindent_style = space\nindent_size = 4\n") == 0,
        "write .editorconfig fixture");
    CHECK_CLEANUP(write_text("sample.c", "int value;\n") == 0,
                  "write source fixture");
    CHECK_CLEANUP(getcwd(cwd, sizeof(cwd)) != NULL,
                  "get working directory");
    path_length = snprintf(source_path, sizeof(source_path), "%s/sample.c", cwd);
    CHECK_CLEANUP(
        path_length > 0 && (size_t)path_length < sizeof(source_path),
        "form absolute source path");
    CHECK_CLEANUP(editorconfig_parse(source_path, handle) == 0,
                  "parse EditorConfig file");

    count = editorconfig_handle_get_name_value_count(handle);
    CHECK_CLEANUP(count >= 2, "parsed property count");
    for (index = 0; index < count; ++index) {
        const char *name = NULL;
        const char *value = NULL;

        editorconfig_handle_get_name_value(handle, index, &name, &value);
        if (name == NULL || value == NULL) {
            fprintf(stderr, "check failed: parsed name-value pair\n");
            status = 1;
            goto cleanup;
        }
        if (strcmp(name, "indent_style") == 0 && strcmp(value, "space") == 0)
            found_indent_style = 1;
        if (strcmp(name, "indent_size") == 0 && strcmp(value, "4") == 0)
            found_indent_size = 1;
    }
    CHECK_CLEANUP(found_indent_style, "indent_style value");
    CHECK_CLEANUP(found_indent_size, "indent_size value");

cleanup:
    if (editorconfig_handle_destroy(handle) != 0) {
        fprintf(stderr, "check failed: handle destruction\n");
        status = 1;
    }
    remove("sample.c");
    remove(".editorconfig");
    if (status == 0)
        printf("EditorConfig %d.%d.%d parse consumer passed\n",
               major, minor, patch);
    return status;
}
