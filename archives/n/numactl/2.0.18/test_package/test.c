#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
#include <numa.h>

int main(void) {
    /* Test that libnuma is linkable and its API is callable.
     * numa_available() calls NUMA syscalls (get_mempolicy) which may
     * trigger SIGSYS on HarmonyOS where the syscall is not implemented.
     * Fork a child to isolate the signal. */
    pid_t pid = fork();
    if (pid == 0) {
        _exit(numa_available() < 0 ? 1 : 0);
    } else if (pid > 0) {
        int status;
        if (waitpid(pid, &status, 0) == -1) {
            perror("waitpid");
            return 1;
        }
        if (WIFSIGNALED(status)) {
            int sig = WTERMSIG(status);
            if (sig == 31) {  /* SIGSYS: NUMA syscall not implemented */
                printf("numactl 2.0.18: libnuma linked OK, NUMA syscall not available (SIGSYS, expected on HarmonyOS)\n");
                return 0;
            }
            printf("numactl 2.0.18: libnuma linked, child killed by signal %d (unexpected)\n", sig);
            return 1;
        }
        if (WIFEXITED(status)) {
            int code = WEXITSTATUS(status);
            if (code == 0) {
                printf("numactl 2.0.18: libnuma linked OK, NUMA available\n");
            } else {
                printf("numactl 2.0.18: libnuma linked OK, NUMA not available (expected on HarmonyOS)\n");
            }
            return 0;
        }
        printf("numactl 2.0.18: unexpected child state\n");
        return 1;
    }
    printf("numactl 2.0.18: fork failed\n");
    return 1;
}
