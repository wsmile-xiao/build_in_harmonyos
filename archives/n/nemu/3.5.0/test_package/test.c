#include <errno.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }

    char *const command[] = {argv[1], (char *)"--version", NULL};
    pid_t child = fork();
    if (child == 0) {
        execv(command[0], command);
        _exit(errno == ENOEXEC ? 126 : 127);
    }
    if (child < 0) {
        return 1;
    }

    int status = 0;
    if (waitpid(child, &status, 0) != child) {
        return 1;
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
