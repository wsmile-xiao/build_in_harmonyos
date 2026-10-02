/*
 * test_lib_consumer.c — thrulay 库 API 消费者端到端测试
 *
 * 真实使用场景（非空壳断言）：
 *   同一进程内 fork() 出服务端（server.h API：init → listen → start），父进程
 *   用 client.h API（options_init → init → start → report_final → exit）对
 *   127.0.0.1 发起一次完整的 TCP 容量测量，并把客户端上报的实测报告解析为断言：
 *   吞吐量必须为正、必须有采样区间行、服务端子进程必须正常退出。
 *
 * 覆盖的公开 API（include/thrulay/{client,server}.h）：
 *   client: thrulay_client_options_init / _init / _start / _report_final / _exit
 *   server: thrulay_server_init / _listen / _start / acl_allow_add
 *   macro : THRULAY_VERSION / STREAMS_MAX / THRULAY_DEFAULT_{SERVER_TCP_PORT,WINDOW}
 *
 * 用法: test_lib_consumer <log_path> [port]
 */
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include <thrulay/client.h>
#include <thrulay/server.h>

#define MAX_LINE 1024

static int g_checks;
static int g_failed;

#define CHECK(cond, ...)                                     \
    do {                                                     \
        g_checks++;                                          \
        if (cond) {                                          \
            printf("  [ok]   " __VA_ARGS__);                 \
            printf("\n");                                    \
        } else {                                             \
            g_failed++;                                      \
            printf("  [FAIL] " __VA_ARGS__);                 \
            printf("\n");                                    \
        }                                                    \
        fflush(stdout);                                      \
    } while (0)

/* 客户端上报的汇总行: "#(**)  0.000  2.000  13098.432  8.014  1.400" */
static double parse_summary_throughput(const char *log_path, int *interval_lines)
{
    FILE *fp = fopen(log_path, "r");
    char line[MAX_LINE];
    double mbps = -1.0;

    *interval_lines = 0;
    if (!fp)
        return -1.0;
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "#(**)", 5) == 0) {
            double begin = 0.0, end = 0.0;
            if (sscanf(line + 5, "%lf %lf %lf", &begin, &end, &mbps) != 3)
                mbps = -1.0;
        } else if (strncmp(line, " (", 2) == 0 || strncmp(line, "(", 1) == 0) {
            (*interval_lines)++;
        }
    }
    fclose(fp);
    return mbps;
}

static int run_server(int port)
{
    /* acl_allow_add() 就地改写实参（server.c: `*pmask++ = '\0'` 拆掉 "/32"），
       因此必须传可写缓冲；传字符串字面量会写入只读段并 SIGSEGV。 */
    char acl[] = "127.0.0.1/32";
    int rc = thrulay_server_init(LOGTYPE_STDERR, 1);
    if (rc < 0) {
        fprintf(stderr, "server_init rc=%d err=%s\n", rc, thrulay_server_strerror(rc));
        return 11;
    }
    rc = acl_allow_add(acl);
    if (rc != 0) {
        fprintf(stderr, "acl_allow_add rc=%d err=%s\n", rc, thrulay_server_strerror(rc));
        return 14;
    }
    fprintf(stderr, "acl_allow_add ok (127.0.0.1/32)\n");
    rc = thrulay_server_listen(port, THRULAY_DEFAULT_WINDOW);
    if (rc < 0) {
        fprintf(stderr, "server_listen rc=%d err=%s\n", rc, thrulay_server_strerror(rc));
        return 12;
    }
    rc = thrulay_server_start(1, NULL); /* 服务 1 个客户端后退出 */
    if (rc < 0) {
        fprintf(stderr, "server_start rc=%d err=%s\n", rc, thrulay_server_strerror(rc));
        return 13;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *log_path = argc > 1 ? argv[1] : "t_lib_consumer.log";
    int port = argc > 2 ? atoi(argv[2]) : 53921;
    thrulay_opt_t opt;
    int saved_stdout;
    FILE *log;
    pid_t pid;
    int status = 0;
    int rc, interval_lines = 0;
    double mbps;

    printf("thrulay lib consumer — port=%d log=%s\n", port, log_path);

    /* ---- [1/4] 头文件编译期契约（宏即库对外契约的一部分） ---- */
    CHECK(strcmp(THRULAY_VERSION, "thrulay/2") == 0,
          "THRULAY_VERSION == thrulay/2 (got %s)", THRULAY_VERSION);
    CHECK(STREAMS_MAX == 256, "STREAMS_MAX == 256 (got %d)", STREAMS_MAX);
    CHECK(THRULAY_DEFAULT_SERVER_TCP_PORT == 5003,
          "THRULAY_DEFAULT_SERVER_TCP_PORT == 5003 (got %d)",
          THRULAY_DEFAULT_SERVER_TCP_PORT);
    CHECK(THRULAY_DEFAULT_WINDOW == 4194304,
          "THRULAY_DEFAULT_WINDOW == 4194304 (got %d)", THRULAY_DEFAULT_WINDOW);

    /* ---- [2/4] 选项默认值（thrulay_client_options_init 真实填充） ---- */
    memset(&opt, 0, sizeof(opt));
    thrulay_client_options_init(&opt);
    CHECK(opt.port == THRULAY_DEFAULT_SERVER_TCP_PORT,
          "options_init port default == %d (got %d)", THRULAY_DEFAULT_SERVER_TCP_PORT, opt.port);
    CHECK(opt.num_streams == 1, "options_init num_streams == 1 (got %d)", opt.num_streams);
    CHECK(opt.reporting_interval == 1,
          "options_init reporting_interval == 1 (got %d)", opt.reporting_interval);
    CHECK(opt.window == THRULAY_DEFAULT_WINDOW,
          "options_init window == %d (got %d)", THRULAY_DEFAULT_WINDOW, opt.window);
    CHECK(opt.rate == 0, "options_init rate == 0 (TCP mode, got %llu)",
          (unsigned long long)opt.rate);

    /* ---- [3/4] fork 服务端 + 客户端 API 真实测量 ---- */
    pid = fork();
    if (pid < 0) {
        perror("fork");
        return 2;
    }
    if (pid == 0)
        _exit(run_server(port));

    sleep(1); /* 等服务端完成 bind/listen（服务端只服务 1 个连接，不做探测连接） */

    opt.server_name = strdup("127.0.0.1");
    opt.port = port;
    opt.test_duration = 2;
    opt.reporting_interval = 1;

    /* 客户端上报走 stdout：重定向到日志文件以便解析实测吞吐量 */
    fflush(stdout);
    saved_stdout = dup(STDOUT_FILENO);
    log = fopen(log_path, "w");
    if (!log) {
        perror("fopen log");
        return 2;
    }
    dup2(fileno(log), STDOUT_FILENO);

    alarm(120); /* 卡死保护：客户端 API 若无法建立会话则超时退出 */
    rc = thrulay_client_init(opt);
    printf("client_init rc=%d\n", rc);
    if (rc >= 0) {
        rc = thrulay_client_start();
        printf("client_start rc=%d\n", rc);
        if (rc < 0)
            printf("client_start err=%s\n", thrulay_client_strerror(rc));
        printf("client_report_final rc=%d\n", thrulay_client_report_final());
    } else {
        printf("client_init err=%s\n", thrulay_client_strerror(rc));
    }
    thrulay_client_exit();
    alarm(0);

    fflush(stdout);
    dup2(saved_stdout, STDOUT_FILENO);
    close(saved_stdout);
    fclose(log);

    waitpid(pid, &status, 0);
    if (WIFSIGNALED(status))
        printf("  [info] server child killed by signal %d\n", WTERMSIG(status));
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0,
          "server child exited cleanly (status=%d)",
          WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    free(opt.server_name);

    /* ---- [4/4] 解析客户端实测报告 ---- */
    mbps = parse_summary_throughput(log_path, &interval_lines);
    CHECK(interval_lines >= 1, "report has %d interval sample line(s)", interval_lines);
    CHECK(mbps > 0.0, "measured TCP throughput > 0 (%.3f Mb/s)", mbps);
    CHECK(mbps > 1.0, "loopback throughput plausible (%.3f Mb/s > 1 Mb/s)", mbps);

    printf("thrulay lib consumer: %d/%d checks passed\n", g_checks - g_failed, g_checks);
    return g_failed == 0 ? 0 : 1;
}
