#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    const char *cron_bin = getenv("CRON_BIN");
    if (cron_bin == NULL || access(cron_bin, X_OK) != 0) {
        fprintf(stderr, "packaged cron binary is unavailable\n");
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
        fprintf(stderr, "cron did not reject the invalid debug flag as expected\n");
        return 1;
    }
    puts("cron consumer test: invalid debug flag rejected");
    return 0;
}
