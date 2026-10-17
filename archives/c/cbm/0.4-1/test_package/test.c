#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
int main(void) {
    int rc = system("cbm >/dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc)) {
        printf("cbm smoke test: cannot run cbm (raw=%d)\n", rc);
        return 1;
    }
    int exit_code = WEXITSTATUS(rc);
    if (exit_code == 127 || exit_code == 126) {
        printf("cbm smoke test: binary missing (exit=%d)\n", exit_code);
        return 1;
    }
    printf("cbm smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
