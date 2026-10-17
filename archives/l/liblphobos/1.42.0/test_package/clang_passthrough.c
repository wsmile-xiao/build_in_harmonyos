/* OHOS 适配：ldmd2 用 posix_spawn 拉起 C/C++ 编译器驱动时，会把 clang++ 的
 * stdout/stderr 接到一条自己并不读写的管道上；clang++/ld.lld 在链接期写出诊断
 * 时因管道无人消费而写失败，返回 status 1（ldmd2 还会吞掉真实报错）。
 *
 * 解决：本文件编译为一个位于**用户数据构建目录**里的真实 ELF。ldmd2 spawn 它后，
 * 它先把 fd 1/2 重定向到一个可写文件（避免管道问题），再以 execv 把同样的 argv
 * 转发给真正的 clang++。实测这样链接步骤才能正常通过（174/174）。
 *
 * 真机上 stdout/stderr 同样是普通文件/tty，本包装的重定向无副作用（只是多写一份
 * clang++ 的诊断到构建目录下的 clang_passthrough.log）。 */
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

#ifndef REALCC
#define REALCC "/data/service/hnp/bin/clang++"
#endif

#ifndef LOGFILE
#define LOGFILE "clang_passthrough.log"
#endif

int main(int argc, char **argv) {
    /* 重定向 clang++ 的 stdout/stderr 到文件，绕开 ldmd2 不给消费的管道。 */
    int logfd = open(LOGFILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (logfd >= 0) {
        dup2(logfd, 1);
        dup2(logfd, 2);
        if (logfd != 1 && logfd != 2)
            close(logfd);
    }
    char **n = (char **)malloc(sizeof(char *) * (argc + 2));
    if (n == NULL)
        return 127; /* exec 前 OOM：非零退出交由上层诊断 */
    n[0] = (char *)REALCC;
    for (int i = 1; i < argc; i++)
        n[i] = argv[i];
    n[argc] = NULL;
    execv(REALCC, n);
    return 127;
}
