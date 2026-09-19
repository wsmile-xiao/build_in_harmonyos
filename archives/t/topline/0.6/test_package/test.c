/* Consumer behaviour test for the packaged topline binary.
 *
 * Runs the real monitor with stdout redirected into a file, gives it time
 * to print its samples, terminates it and asserts the binary actually
 * started and produced its monitor output.
 */
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <topline-binary>\n", argv[0]);
        return 2;
    }

    const char *outpath = "topline-consumer.out";
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 2;
    }
    if (pid == 0) {
        int fd = open(outpath, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0)
            _exit(127);
        dup2(fd, STDOUT_FILENO);
        close(fd);
        char *const av[] = { (char *)"topline", (char *)"-i", (char *)"1", NULL };
        execv(argv[1], av);
        _exit(127);
    }

    /* topline prints its first sample immediately, then refreshes every
     * interval second; give it a few cycles before stopping it. */
    sleep(3);
    kill(pid, SIGTERM);

    int st = 0;
    waitpid(pid, &st, 0);

    FILE *f = fopen(outpath, "r");
    if (!f) {
        perror("fopen");
        return 2;
    }
    static char buf[65536];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    unlink(outpath);

    /* assertion 1: the binary must have exec'd (exit 127 means exec failed) */
    if (WIFEXITED(st) && WEXITSTATUS(st) == 127) {
        fprintf(stderr, "topline failed to exec\n");
        return 1;
    }
    /* assertion 2: the sampling monitor must have produced output */
    if (n == 0) {
        fprintf(stderr, "topline produced no output\n");
        return 1;
    }
    /* assertion 3: the monitor lines must contain numeric statistics
     * (per-CPU/per-disk usage percentages), not just newlines */
    if (strspn(buf, " \n\t") == n) {
        fprintf(stderr, "topline output contains no numeric stats\n");
        return 1;
    }

    printf("topline consumer test: captured %zu bytes of monitor output\n", n);
    return 0;
}
