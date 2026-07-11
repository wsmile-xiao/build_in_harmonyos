#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

#ifdef BIRD_BIN
#define BIRD_CMD BIRD_BIN " --version"
#else
#define BIRD_CMD "bird --version"
#endif

int main(void) {
    /* L2 smoke test: verify bird binary is executable and reports version */
    int ret = system(BIRD_CMD);
    if (ret != 0) {
        fprintf(stderr, "FAIL: %s exited with %d\n", BIRD_CMD, WEXITSTATUS(ret));
        return 1;
    }
    printf("bird binary smoke test: OK\n");
    return 0;
}
