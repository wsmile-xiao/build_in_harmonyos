#include <elf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int check(const char *bin, const char *window, const char *expected,
                 const char *emulator) {
    int input[2], output[2];
    if (pipe(input) || pipe(output)) return 1;
    pid_t pid = fork();
    if (pid < 0) return 1;
    if (pid == 0) {
        dup2(input[0], STDIN_FILENO);
        dup2(output[1], STDOUT_FILENO);
        close(input[0]); close(input[1]); close(output[0]); close(output[1]);
        if (emulator && window)
            execl(emulator, emulator, bin, "-w", window, (char *)NULL);
        else if (emulator)
            execl(emulator, emulator, bin, (char *)NULL);
        else if (window) execl(bin, bin, "-w", window, (char *)NULL);
        else execl(bin, bin, (char *)NULL);
        _exit(127);
    }
    close(input[0]); close(output[1]);
    const char *lines = "a\nb\na\na\nc\na\n";
    if (write(input[1], lines, strlen(lines)) != (ssize_t)strlen(lines)) return 1;
    close(input[1]);
    char result[128] = {0};
    size_t used = 0;
    ssize_t count;
    while ((count = read(output[0], result + used, sizeof(result) - used - 1)) > 0)
        used += (size_t)count;
    close(output[0]);
    int status;
    if (waitpid(pid, &status, 0) != pid) return 1;
    return count == 0 && WIFEXITED(status) && WEXITSTATUS(status) == 0 &&
           strcmp(result, expected) == 0 ? 0 : 1;
}

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3) return 2;
    const char *emulator = argc == 3 ? argv[2] : NULL;
    /* OHOS PC consumer: verify installed target ELF, then exercise libc pipe/fork/exec. */
    FILE *f = fopen(argv[1], "rb");
    unsigned char header[20];
    if (!f || fread(header, 1, sizeof(header), f) != sizeof(header)) return 3;
    fclose(f);
    if (memcmp(header, ELFMAG, SELFMAG) || header[18] != EM_AARCH64 || header[19]) return 4;
    if (check(argv[1], "2", "a\nb\nc\na\n", emulator)) return 5;
    if (check(argv[1], NULL, "a\nb\nc\n", emulator)) return 6;
    puts("OHOS aarch64 ELF and sliding-window pipe consumer: PASS (2/2)");
    return 0;
}
