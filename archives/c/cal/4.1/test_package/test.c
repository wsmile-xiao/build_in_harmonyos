#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
int main(void) {
    int rc = system("cal >/dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc)) {
        printf("cal smoke test: cannot run cal (raw=%d)\n", rc);
        return 1;
    }
    int exit_code = WEXITSTATUS(rc);
    if (exit_code == 127 || exit_code == 126) {
        printf("cal smoke test: binary missing (exit=%d)\n", exit_code);
        return 1;
    }
    printf("cal smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
