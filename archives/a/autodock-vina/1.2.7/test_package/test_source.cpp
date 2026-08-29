#include <sys/wait.h>
#include <unistd.h>

#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
    if (argc != 2) {
        return 2;
    }

    int output[2];
    if (pipe(output) != 0) {
        return 3;
    }

    const pid_t child = fork();
    if (child == 0) {
        dup2(output[1], STDOUT_FILENO);
        close(output[0]);
        close(output[1]);
        execl(argv[1], argv[1], "--version", static_cast<char*>(nullptr));
        _exit(127);
    }
    if (child < 0) {
        return 4;
    }

    close(output[1]);
    char buffer[4096] = {};
    const ssize_t length = read(output[0], buffer, sizeof(buffer) - 1);
    close(output[0]);

    int status = 0;
    waitpid(child, &status, 0);
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0 || length <= 0) {
        return 5;
    }
    buffer[length] = '\0';
    return std::strstr(buffer, "AutoDock Vina") != nullptr &&
                   std::strstr(buffer, "1.2.7") != nullptr
               ? 0
               : 6;
}
