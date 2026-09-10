#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
int main() {
    int rc = system("ccmix >/dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc)) {
        printf("ccmix smoke test: cannot run ccmix (raw=%d)\n", rc);
        return 1;
    }
    int exit_code = WEXITSTATUS(rc);
    if (exit_code == 127 || exit_code == 126) {
        printf("ccmix smoke test: binary missing (exit=%d)\n", exit_code);
        return 1;
    }
    if (exit_code > 128) {
        printf("ccmix smoke test: binary crashed (exit=%d)\n", exit_code);
        return 1;
    }
    printf("ccmix smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
