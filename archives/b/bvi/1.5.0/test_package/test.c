#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <stdlib.h>

/* bvi is a terminal editor (ncurses); --version may fail without a PTY.
 * We verify the binary actually starts by fork+exec and checking
 * that it exits normally (WIFEXITED), not "not found" (127). */
int main(int argc, char *argv[])
{
    if (argc < 2)
        return 1;

    pid_t pid = fork();
    if (pid == -1)
        return 1;
    if (pid == 0) {
        char *args[] = {argv[1], "--version", NULL};
        execv(argv[1], args);
        _exit(127); /* exec failed */
    }

    int status;
    if (waitpid(pid, &status, 0) == -1)
        return 1;
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);
        /* 127 = exec failed; any other code = binary started and ran */
        return (code == 127) ? 1 : 0;
    }
    /* Killed by signal = binary started but crashed */
    return 1;
}
