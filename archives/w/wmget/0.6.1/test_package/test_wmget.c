/*
 * test_wmget.c — wmget 0.6.1 test_package 冒烟（R34 真实产物校验）
 *
 * 1) 产物 ELF 校验：\x7fELF magic + e_machine=EM_AARCH64(183)；
 * 2) fork/exec 真跑 `wmget --version`：期望退出码 0；
 * 3) fork/exec 真跑 `wmget --help`：期望退出码 0。
 *
 * CLI 子命令不触碰 X11 显示，可无头运行；依赖的共享库由 conanrun 环境
 * （LD_LIBRARY_PATH）提供，exec 后的子进程继承。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/wait.h>

#ifndef WMGET_BIN_PATH
#define WMGET_BIN_PATH "wmget"
#endif

static int fail(const char *msg)
{
    fprintf(stderr, "FAIL: %s\n", msg);
    return 1;
}

/* 返回被测进程退出码；<0 = fork/wait 异常或被信号杀死 */
static int run_wmget(const char *path, const char *arg)
{
    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        /* 输出丢弃，只关心退出码 */
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) {
            dup2(devnull, 1);
            dup2(devnull, 2);
        }
        execl(path, "wmget", arg, (char *)0);
        _exit(127); /* execl 失败 */
    }
    int st = 0;
    if (waitpid(pid, &st, 0) < 0)
        return -1;
    if (WIFSIGNALED(st))
        return -2;
    return WIFEXITED(st) ? WEXITSTATUS(st) : -3;
}

int main(void)
{
    const char *bin = WMGET_BIN_PATH;

    /* 1) ELF 产物校验 */
    FILE *f = fopen(bin, "rb");
    if (!f)
        return fail("cannot open wmget binary");
    unsigned char eh[20];
    size_t got = fread(eh, 1, sizeof eh, f);
    fclose(f);
    if (got != sizeof eh)
        return fail("short read of ELF header");
    if (eh[0] != 0x7f || eh[1] != 'E' || eh[2] != 'L' || eh[3] != 'F')
        return fail("bad ELF magic");
    if (eh[0x12] != 183) /* e_machine 低字节 = EM_AARCH64 */
        return fail("not an EM_AARCH64 (183) binary");

    /* 2) --version 真跑 */
    int rc = run_wmget(bin, "--version");
    if (rc != 0) {
        fprintf(stderr, "wmget --version rc=%d\n", rc);
        return fail("wmget --version did not exit 0");
    }

    /* 3) --help 真跑 */
    rc = run_wmget(bin, "--help");
    if (rc != 0) {
        fprintf(stderr, "wmget --help rc=%d\n", rc);
        return fail("wmget --help did not exit 0");
    }

    printf("wmget test_package: ELF OK (aarch64); --version/--help rc=0\n");
    return 0;
}
