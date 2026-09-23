#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>

/* 验证命令以指定退出码正常退出 */
static int run_and_check_exit(const char *cmd, int expected) {
    pid_t pid = fork();
    if (pid == 0) {
        execlp(cmd, cmd, NULL);
        perror("execlp");
        exit(127);
    }
    int status;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);
        if (code == expected) {
            return 0;
        }
        fprintf(stderr, "%s: expected exit %d, got %d\n", cmd, expected, code);
        return 1;
    }
    fprintf(stderr, "%s: expected exit %d, but terminated by signal\n", cmd, expected);
    return 1;
}

/* 验证命令以非零退出码或被信号终止（崩溃类行为） */
static int run_and_check_crash(const char *cmd) {
    pid_t pid = fork();
    if (pid == 0) {
        execlp(cmd, cmd, NULL);
        perror("execlp");
        exit(127);
    }
    int status;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);
        if (code != 0) {
            return 0;  /* 非零退出码，视为崩溃 */
        }
        fprintf(stderr, "%s: expected crash, got clean exit 0\n", cmd);
        return 1;
    } else if (WIFSIGNALED(status)) {
        return 0;  /* 被信号终止，视为崩溃 */
    }
    fprintf(stderr, "%s: terminated abnormally\n", cmd);
    return 1;
}

int main(void) {
    int ret = 0;
    /* divide-by-zero: 鸿蒙平台返回 0（无 SIGFPE） */
    ret |= run_and_check_exit("divide-by-zero", 0);
    /* seg-fault: 预期非零退出码或被 SIGSEGV 等信号终止 */
    ret |= run_and_check_crash("seg-fault");
    return ret;
}
