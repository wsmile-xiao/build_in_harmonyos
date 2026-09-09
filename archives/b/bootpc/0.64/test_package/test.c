#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
int main(void) {
    int rc = system("bootpc >/dev/null 2>&1");
    int exit_code = -1;
    if (WIFEXITED(rc))
        exit_code = WEXITSTATUS(rc);
    if (exit_code == 127 || exit_code == 126 || rc == -1) {
        printf("bootpc smoke test: binary missing (exit=%d)\n", exit_code);
        return 1;
    }
    printf("bootpc smoke test: binary executes (exit=%d)\n", exit_code);
    return 0;
}
