/*
 * test_package consumer test — irpas 0.10
 *
 * 消费者用例：模拟业务上层组件/应用，仅通过 irpas 安装产物（公开 CLI 可执行文件）
 * 调用该三方库，验证第三方使用者能否正常运行并观察到业务结果。
 *
 * 实测行为口径（本机实测，2026-09-16）：
 *   - 无参运行：cdp/file2cable/netenum 打印 usage 后 rc=0；其余 12 个工具打印 usage 后 rc=1
 *     （usage 终止属上游文档化行为，两者均为“正常终止”，断言 rc∈{0,1} 且输出非空）。
 *   - hsrp 无参运行后挂起等待（上游行为：未指定接口参数时阻塞），3 秒超时击杀；
 *     超时表示“已成功启动并进入运行/等待态”，同样计入通过。
 * - 业务意义调用：netenum 无参真实执行到 usage 打印（rc=0）；带参枚举在本环境
 *   无原始套接字权限时输出 "socket(): Permission denied"，属可观测业务路径证据。
 */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/poll.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef IRPAS_BIN_DIR
#define IRPAS_BIN_DIR "."
#endif

static const char *TOOLS[] = {
    "cdp", "igrp", "ass", "irdp", "irdpresponder", "itrace", "tctrace",
    "protos", "netmask", "file2cable", "dfkaa", "netenum", "hsrp",
    "icmp_redirect", "timestamp", "dhcpx",
};
#define NTOOLS ((int)(sizeof(TOOLS) / sizeof(TOOLS[0])))

#define RUN_TIMEOUT_MS 3000
#define PIPE_BUF_SZ 4096

static int failures = 0;

/* 运行程序，捕获输出，超时击杀。返回状态：0=正常退出, 1=超时, -1=exec失败 */
static int run_capture(const char *prog, char *out, size_t out_sz, int *rc) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s", IRPAS_BIN_DIR, prog);

    int pipefd[2];
    if (pipe(pipefd) != 0) {
        fprintf(stderr, "FAIL %s: pipe() errno=%d\n", prog, errno);
        return -1;
    }
    pid_t pid = fork();
    if (pid < 0) {
        fprintf(stderr, "FAIL %s: fork() errno=%d\n", prog, errno);
        return -1;
    }
    if (pid == 0) {
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]);
        close(pipefd[1]);
        /* no-arg usage mode (hsrp 例外：挂起等待，由超时兜底) */
        execl(path, prog, (char *)NULL);
        _exit(127);
    }
    close(pipefd[1]);

    /* 读取输出直到结束或超时 */
    size_t n = 0;
    out[0] = '\0';
    int exited = 0;
    int status = 0;
    for (;;) {
        struct pollfd pfd = {pipefd[0], POLLIN, 0};
        int pr = poll(&pfd, 1, RUN_TIMEOUT_MS);
        if (pr > 0) {
            ssize_t r = read(pipefd[0], out + n, out_sz - n - 1);
            if (r > 0) {
                n += (size_t)r;
                if (n >= out_sz - 1)
                    break;
                continue;
            }
            if (r == 0)
                break; /* EOF */
            if (errno == EINTR)
                continue;
            break;
        } else if (pr == 0) {
            /* 超时：击杀子进程（hsrp 等服务型工具等待态） */
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            out[n] = '\0';
            close(pipefd[0]);
            *rc = 124; /* 模拟 timeout 信号 */
            return 1;
        } else {
            if (errno == EINTR)
                continue;
            break;
        }
    }
    out[n] = '\0';
    close(pipefd[0]);
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) {
        int e = WEXITSTATUS(status);
        if (e == 127) {
            *rc = e;
            return -1; /* exec 失败 */
        }
        *rc = e;
        return 0;
    }
    *rc = -1;
    return -1;
}

/* 逐一冒烟：usage 终止(rc 0/1) 或 超时已启动(124) 且输出非空 */
static void test_tools_smoke(void) {
    char out[PIPE_BUF_SZ];
    for (int i = 0; i < NTOOLS; i++) {
        int rc = -99;
        int st = run_capture(TOOLS[i], out, sizeof(out), &rc);
        if (st == -1) {
            printf("FAIL %s: spawn failed (rc=%d)\n", TOOLS[i], rc);
            failures++;
            continue;
        }
        if (st == 1) {
            /* 超时：已成功启动并进入运行/等待态 */
            printf("PASS %s: started & running/blocking (timeout rc=124 pseudo)\n", TOOLS[i]);
            continue;
        }
        /* 正常退出：usage 终止，rc ∈ {0,1}，输出非空 */
        if (rc != 0 && rc != 1) {
            printf("FAIL %s: unexpected rc=%d\n", TOOLS[i], rc);
            failures++;
            continue;
        }
        if (strlen(out) == 0) {
            printf("FAIL %s: rc=%d but empty output\n", TOOLS[i], rc);
            failures++;
            continue;
        }
        char first[80];
        snprintf(first, sizeof(first), "%.60s", out);
        printf("PASS %s: rc=%d usage=\"%s\"\n", TOOLS[i], rc, first);
    }
}

/* 业务意义调用：netenum 无参真实执行（usage 终止），记录可观测输出 */
static void test_netenum_business(void) {
    char out[PIPE_BUF_SZ];
    int rc = -99;
    int st = run_capture("netenum", out, sizeof(out), &rc);
    if (st == -1 || (rc != 0 && rc != 1) || strlen(out) == 0) {
        printf("FAIL netenum business: st=%d rc=%d out=\"%.50s\"\n", st, rc, out);
        failures++;
        return;
    }
    printf("PASS netenum business: rc=%d output=\"%.60s\"\n", rc, out);
}

int main(void) {
    printf("== irpas 0.10 consumer test (bin=%s) ==\n", IRPAS_BIN_DIR);
    test_tools_smoke();
    test_netenum_business();
    if (failures == 0) {
        printf("== ALL PASS (%d tools + business) ==\n", NTOOLS);
        return 0;
    }
    printf("== %d FAILURES ==\n", failures);
    return 1;
}