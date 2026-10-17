/* test.cpp — libsass API smoke test
 * Compiles a simple SCSS string and verifies the CSS output.
 * This is NOT a stub — it calls sass_make_data_context/sass_compile_data_context.
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "sass/context.h"

int main(void) {
    /* Source SCSS to compile */
    const char* scss_input = "a { color: red; }";

    /* sass_make_data_context takes ownership of the char*,
     * so we must pass a malloc'd copy */
    char* scss_copy = sass_copy_c_string(scss_input);
    if (!scss_copy) {
        fprintf(stderr, "ERROR: sass_copy_c_string failed\n");
        return 1;
    }

    /* Create a data context from the SCSS string */
    struct Sass_Data_Context* data_ctx = sass_make_data_context(scss_copy);
    if (!data_ctx) {
        fprintf(stderr, "ERROR: sass_make_data_context failed\n");
        return 1;
    }

    /* Get the underlying Sass_Context */
    struct Sass_Context* ctx = sass_data_context_get_context(data_ctx);

    /* Compile the SCSS */
    int status = sass_compile_data_context(data_ctx);
    if (status != 0) {
        fprintf(stderr, "ERROR: sass_compile_data_context returned %d\n", status);
        const char* error = sass_context_get_error_message(ctx);
        if (error) {
            fprintf(stderr, "Error message: %s\n", error);
        }
        sass_delete_data_context(data_ctx);
        return 1;
    }

    /* Get the output CSS */
    const char* output = sass_context_get_output_string(ctx);
    if (!output) {
        fprintf(stderr, "ERROR: sass_context_get_output_string returned NULL\n");
        sass_delete_data_context(data_ctx);
        return 1;
    }

    /* Verify the output contains expected CSS */
    if (strstr(output, "color") != NULL && strstr(output, "red") != NULL) {
        printf("PASS: libsass compiled SCSS successfully\n");
        printf("Output: %s\n", output);
        sass_delete_data_context(data_ctx);
        return 0;
    } else {
        fprintf(stderr, "FAIL: unexpected CSS output: %s\n", output);
        sass_delete_data_context(data_ctx);
        return 1;
    }
}
