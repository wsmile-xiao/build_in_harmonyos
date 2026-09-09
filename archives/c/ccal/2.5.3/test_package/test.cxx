#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
int main() {
    int rc = system("ccal >/dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc)) {
        printf("ccal smoke test: cannot run ccal (raw=%d)\n", rc);
        return 1;
    }
    int exit_code = WEXITSTATUS(rc);
    if (exit_code == 127 || exit_code == 126) {
        printf("ccal smoke test: binary missing (exit=%d)\n", exit_code);
        return 1;
    }
    printf("ccal smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
