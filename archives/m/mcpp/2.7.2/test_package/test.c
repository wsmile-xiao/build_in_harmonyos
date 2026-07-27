#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "mcpp_lib.h"

#define OUTPUT_BUFFER_SIZE 4096

static int report_failure(const char *message)
{
    if (fputs(message, stderr) == EOF) {
        return 2;
    }
    return 1;
}

static int cleanup_file(
    const char *path,
    const char *message,
    int missing_ok,
    int result
)
{
    int cleanup_result;

    if (remove(path) == 0) {
        return result;
    }
    if (missing_ok && errno == ENOENT) {
        return result;
    }
    cleanup_result = report_failure(message);
    return result != 0 ? result : cleanup_result;
}

static int cleanup_files(
    const char *input_path,
    const char *output_path,
    int output_may_be_missing,
    int result
)
{
    result = cleanup_file(
        output_path,
        "failed to remove API test output\n",
        output_may_be_missing,
        result
    );
    return cleanup_file(
        input_path,
        "failed to remove API test input\n",
        0,
        result
    );
}

static int read_output_file(
    const char *path,
    char *buffer,
    size_t capacity
)
{
    FILE *output = fopen(path, "rb");
    size_t length;
    int result = 0;

    if (output == NULL) {
        return report_failure("failed to open libmcpp output\n");
    }

    length = fread(buffer, 1, capacity - 1, output);
    if (ferror(output)) {
        result = report_failure("failed to read libmcpp output\n");
    } else {
        int extra = fgetc(output);

        if (extra != EOF) {
            result = report_failure("libmcpp output exceeds test buffer\n");
        } else if (ferror(output)) {
            result = report_failure("failed to finish reading libmcpp output\n");
        } else {
            buffer[length] = '\0';
        }
    }

    if (fclose(output) != 0) {
        int close_result = report_failure("failed to close libmcpp output\n");

        if (result == 0) {
            result = close_result;
        }
    }
    return result;
}

int main(void)
{
    const char *input_path = "mcpp_api_input.c";
    const char *output_path = "mcpp_api_output.i";
    FILE *input = fopen(input_path, "w");
    char arg0[] = "mcpp";
    char arg1[] = "-P";
    char arg2[] = "mcpp_api_input.c";
    char arg3[] = "-o";
    char arg4[] = "mcpp_api_output.i";
    char *argv[] = {arg0, arg1, arg2, arg3, arg4, NULL};
    char output[OUTPUT_BUFFER_SIZE];
    int status;

    if (input == NULL) {
        return report_failure("failed to create API test input\n");
    }
    if (fputs("#define MCPP_API_TOKEN 314159\n"
              "int mcpp_api_value = MCPP_API_TOKEN;\n", input) == EOF) {
        int close_status = fclose(input);
        int result;

        if (close_status != 0) {
            result = report_failure(
                "failed to write and close API test input\n"
            );
        } else {
            result = report_failure("failed to write API test input\n");
        }
        return cleanup_file(
            input_path,
            "failed to remove API test input\n",
            0,
            result
        );
    }
    if (fclose(input) != 0) {
        return cleanup_file(
            input_path,
            "failed to remove API test input\n",
            0,
            report_failure("failed to close API test input\n")
        );
    }

    status = mcpp_lib_main(5, argv);

    if (status != 0) {
        int result = 1;

        if (fprintf(stderr, "mcpp_lib_main returned %d\n", status) < 0) {
            result = 2;
        }
        return cleanup_files(input_path, output_path, 1, result);
    }
    status = read_output_file(output_path, output, sizeof(output));
    if (status != 0) {
        return cleanup_files(input_path, output_path, 0, status);
    }
    if (strstr(output, "314159") == NULL
            || strstr(output, "MCPP_API_TOKEN") != NULL) {
        int result = 1;

        if (fprintf(stderr, "unexpected libmcpp output:\n%s\n", output) < 0) {
            result = 2;
        }
        return cleanup_files(input_path, output_path, 0, result);
    }

    status = cleanup_files(input_path, output_path, 0, 0);
    if (status != 0) {
        return status;
    }
    if (puts("libmcpp API test passed") == EOF) {
        return 2;
    }
    return 0;
}
