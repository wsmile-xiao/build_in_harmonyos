#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char path[] = "./xtail-test-XXXXXX";
    char buf[4096] = {0};
    int fd, output[2], found = 0;
    pid_t child;
    size_t used = 0;
    struct timeval tv;

    if (argc != 2 || (fd = mkstemp(path)) < 0 || pipe(output) < 0)
        return 1;
    write(fd, "initial\n", 8);
    child = fork();
    if (child == 0) {
        dup2(output[1], STDOUT_FILENO);
        close(output[0]);
        close(output[1]);
        execl(argv[1], argv[1], path, (char *)NULL);
        _exit(127);
    }
    close(output[1]);
    if (child < 0) {
        close(fd);
        unlink(path);
        return 1;
    }
    /* Let xtail observe the initial size before appending. */
    tv.tv_sec = 1;
    tv.tv_usec = 200000;
    select(0, NULL, NULL, NULL, &tv);
    write(fd, "XT-APPENDED\n", 12);
    fsync(fd);
    tv.tv_sec = 6;
    tv.tv_usec = 0;
    while (used < sizeof(buf) - 1) {
        fd_set readfds;
        int ready;
        FD_ZERO(&readfds);
        FD_SET(output[0], &readfds);
        ready = select(output[0] + 1, &readfds, NULL, NULL, &tv);
        if (ready <= 0)
            break;
        int n = read(output[0], buf + used, sizeof(buf) - 1 - used);
        if (n <= 0)
            break;
        used += (size_t)n;
        buf[used] = '\0';
        if (strstr(buf, "XT-APPENDED") != NULL) {
            found = 1;
            break;
        }
    }
    kill(child, SIGTERM);
    waitpid(child, NULL, 0);
    close(output[0]);
    close(fd);
    unlink(path);
    if (!found)
        fprintf(stderr, "xtail did not print the appended data: %s\n", buf);
    return found ? 0 : 1;
}
