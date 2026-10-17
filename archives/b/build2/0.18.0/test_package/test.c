#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(__OHOS__) || defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <sys/wait.h>
#define BUILD2_POSIX_WAIT_STATUS 1
#endif

int main(void)
{
    int status = system("build2 --version > build2-version.txt 2>&1");
#if defined(BUILD2_POSIX_WAIT_STATUS)
    if (status == -1 || !WIFEXITED(status) || WEXITSTATUS(status) != 0)
        return 1;
#else
    if (status != 0)
        return 1;
#endif

    FILE *stream = fopen("build2-version.txt", "rb");
    if (stream == NULL)
        return 1;

    char output[4096];
    size_t length = fread(output, 1, sizeof(output) - 1, stream);
    fclose(stream);
    output[length] = '\0';

    return strstr(output, "build2 ") != NULL &&
                   strstr(output, "libbutl ") != NULL
               ? 0
               : 1;
}
