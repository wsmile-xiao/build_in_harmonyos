#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
int main(void) {
    int rc = system("cbmbasic >/dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc)) {
        printf("cbmbasic smoke test: cannot run cbmbasic (raw=%d)\n", rc);
        return 1;
    }
    int exit_code = WEXITSTATUS(rc);
    if (exit_code != 0) {
        printf("cbmbasic smoke test: binary missing or failed to run (exit=%d)\n", exit_code);
        return 1;
    }
    printf("cbmbasic smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
