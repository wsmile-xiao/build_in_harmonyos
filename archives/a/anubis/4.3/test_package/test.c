/* Real consumer test for the installed anubis CLI (R34). */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static int run_capture(const char *binary, const char *argument,
                       char *output, size_t output_size)
{
    char command[1024];
    FILE *pipe;
    size_t length;
    int status;

    if (snprintf(command, sizeof(command), "\"%s\" %s 2>&1",
                 binary, argument) >= (int)sizeof(command))
        return -1;
    pipe = popen(command, "r");
    if (pipe == NULL)
        return -1;
    length = fread(output, 1, output_size - 1, pipe);
    output[length] = '\0';
    status = pclose(pipe);
    if (status == -1 || !WIFEXITED(status))
        return -1;
    return WEXITSTATUS(status);
}

static int check(int condition, const char *description)
{
    if (condition)
        printf("PASS: %s\n", description);
    else
        printf("FAIL: %s\n", description);
    return condition ? 0 : 1;
}

int main(int argc, char **argv)
{
    char output[2048];
    int failures = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s /path/to/anubis\n", argv[0]);
        return 1;
    }

    failures += check(
        run_capture(argv[1], "--version", output, sizeof(output)) == 0 &&
        strstr(output, "GNU Anubis 4.3") != NULL,
        "anubis --version reports GNU Anubis 4.3");

    failures += check(
        run_capture(argv[1], "--show-config-options", output, sizeof(output)) == 0,
        "anubis --show-config-options exits successfully");

    if (failures != 0) {
        printf("%d consumer test(s) failed\n", failures);
        return 1;
    }
    printf("All consumer tests passed\n");
    return 0;
}
