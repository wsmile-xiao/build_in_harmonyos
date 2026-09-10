// test_prg_exec_monitor.cpp — boost1.84-prg_exec_monitor 1.84.0 L1 测试
//
// R34：实质调用被测包 API/语义：
//   1. 正常路径：cpp_main 返回 0 → PEM 以退出码 0 报告成功
//   2. 错误路径：子进程内 cpp_main 返回 5 → PEM 捕获并以非零退出码
//      报告（"errors detected; see standard output for details"），
//      主进程 waitpid 断言子进程非零退出——验证 PEM 核心转译语义
//   3. 抛异常路径：子进程内 cpp_main 抛 C 字符串异常 → PEM 捕获
//      （uncaught exception）非零退出
#include <boost/test/prg_exec_monitor.hpp>

#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>
#include <unistd.h>

int cpp_main(int argc, char* argv[])
{
    // ---- 场景 2/3：子进程验证 PEM 错误转译（通过命令行参数分派）----
    if (argc > 1) {
        if (argv[1][0] == 'r') {          // "r*" → 返回非零 5
            return 5;
        }
        if (argv[1][0] == 't') {          // "t*" → 抛未捕获 C 字符串异常
            throw "PEM smoke: intentional C-string exception";
        }
        return 0;
    }

    // ---- 场景 1：正常路径（本进程），返回 0 → 退出码必须为 0 ----
    // 场景 2：子进程跑 "r5"（cpp_main 返回 5）
    pid_t pid_r = fork();
    if (pid_r == 0) {
        execl(argv[0], argv[0], "r5", (char*)0);
        _exit(127);                       // execl 失败兜底
    }
    int st_r = 0;
    waitpid(pid_r, &st_r, 0);
    if (!WIFEXITED(st_r)) {
        std::fprintf(stderr, "scenario-return: child not exited normally\n");
        return 1;
    }
    int rc_r = WEXITSTATUS(st_r);
    // PEM 把 cpp_main 非零返回转译为非零退出码（报告 error return code: 5）
    if (rc_r == 0) {
        std::fprintf(stderr, "scenario-return: PEM did not translate nonzero return\n");
        return 1;
    }

    // 场景 3：子进程跑 "throw"（cpp_main 抛 C 字符串异常）
    pid_t pid_t = fork();
    if (pid_t == 0) {
        execl(argv[0], argv[0], "throw", (char*)0);
        _exit(127);
    }
    int st_t = 0;
    waitpid(pid_t, &st_t, 0);
    if (!WIFEXITED(st_t)) {
        std::fprintf(stderr, "scenario-throw: child not exited normally\n");
        return 1;
    }
    int rc_t = WEXITSTATUS(st_t);
    // PEM 捕获未捕获异常 → 非零退出码
    if (rc_t == 0) {
        std::fprintf(stderr, "scenario-throw: PEM did not catch exception\n");
        return 1;
    }

    std::printf("boost1.84-prg_exec_monitor test_package PASSED "
                "(normal rc=0 / nonzero-return translated rc=%d / "
                "uncaught-exception caught rc=%d)\n", rc_r, rc_t);
    return 0;
}
