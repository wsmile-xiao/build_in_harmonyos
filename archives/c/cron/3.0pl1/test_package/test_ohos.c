#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef __OHOS__
#error "This consumer test must be compiled for HarmonyOS"
#endif

int main(void) {
    const char *cron_bin = getenv("CRON_BIN_OHOS");
    if (cron_bin == NULL || access(cron_bin, X_OK) != 0) {
        fprintf(stderr, "OHOS consumer test cannot access packaged cron\n");
        return 1;
    }

    pid_t child = fork();
    if (child < 0) {
        perror("fork");
        return 1;
    }
    if (child == 0) {
        execl(cron_bin, cron_bin, "-x", "invalid", (char *)NULL);
        _exit(127);
    }

    int status;
    if (waitpid(child, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) == 0 || WEXITSTATUS(status) == 127) {
        fprintf(stderr, "OHOS packaged cron did not reject the invalid debug flag\n");
        return 1;
    }
    puts("OHOS consumer test: packaged cron executed successfully");
    return 0;
}
