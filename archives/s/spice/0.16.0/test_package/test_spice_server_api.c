/*
 * Consumer contract test for spice 0.16.0 (libspice-server).
 *
 * 以真实消费者（qemu 之外的最小代表性调用序列）的方式链接并使用导出的
 * C ABI：spice_server_new → set_port / set_name / set_ticket → destroy。
 * 调用序列与上游 server/tests/test-set-ticket.c 的未连接期路径一致
 * （reds.cpp: spice_server_new/destroy 在未 spice_server_init() 前安全，
 *  set_port 纯配置写入，set_ticket 未连接时直接写入票据，见 0.16.0 源码）。
 *
 * 每个用例输出 "TEST PASS - ..." / "TEST FAIL - ..."，结尾输出
 * "TEST SUMMARY: N/N passed"；任一失败进程退出码 1。
 */
#include <stdio.h>

#include <spice-server/spice.h>

static int tests_run = 0;
static int tests_failed = 0;

static void check(int cond, const char *what)
{
    tests_run++;
    if (cond) {
        printf("TEST PASS - %s\n", what);
    } else {
        printf("TEST FAIL - %s\n", what);
        tests_failed++;
    }
    fflush(stdout);
}

int main(void)
{
    SpiceServer *server;

    /* spice.h → spice-server.h → spice-version.h：版本宏必须可见且非零。 */
    printf("info - SPICE_SERVER_VERSION = 0x%06x\n", SPICE_SERVER_VERSION);
    check(SPICE_SERVER_VERSION > 0, "SPICE_SERVER_VERSION macro visible and non-zero");

    server = spice_server_new();
    check(server != NULL, "spice_server_new() returns a server instance");
    if (server == NULL) {
        printf("TEST SUMMARY: %d/%d passed\n", tests_run - tests_failed, tests_run);
        return 1;
    }

    /* 端口配置：合法端口接受（0），越界拒绝（-1）。 */
    check(spice_server_set_port(server, 5912) == 0,
          "spice_server_set_port(5912) accepted");
    check(spice_server_set_port(server, 70000) == -1,
          "spice_server_set_port(70000) rejected out of range");

    /* 服务器名（qemu -name 语义），void API 可调用且不崩溃。 */
    spice_server_set_name(server, "spice-ohos-consumer-test");
    check(1, "spice_server_set_name() callable with a server name");

    /* 无过期票据（lifetime=0 → 永不过期）；未连接时 fail/disconnect 标志
     * 不触发，返回 0。 */
    check(spice_server_set_ticket(server, "ohos-tp-ticket", 0, 1, 1) == 0,
          "spice_server_set_ticket(passwd, lifetime=0, fail=1, disconnect=1) accepted");

    /* 空密码（无认证）同一路径。 */
    check(spice_server_set_ticket(server, NULL, 0, 1, 1) == 0,
          "spice_server_set_ticket(NULL passwd) accepted");

    /* 未 init 的 server 可直接销毁（上游契约：destroy 对未初始化实例安全）。 */
    spice_server_destroy(server);
    check(1, "spice_server_destroy() tears the server down");

    printf("TEST SUMMARY: %d/%d passed\n", tests_run - tests_failed, tests_run);
    return tests_failed == 0 ? 0 : 1;
}
