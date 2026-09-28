/*
 * test_ohos.c — HarmonyOS 专项测试（区别于上游测试与 test_package 消费者单测）
 *
 * 验证 embedded-log 库在 HarmonyOS PC (aarch64-linux-ohos, musl libc) 目标上
 * 的真实行为：log_init 注册 hook 后，LOG_ERR/LOG_WRN/LOG_INF 各级别宏经
 * printk() 格式化并通过 hook 回调输出，printk_hex() 以十六进制转储缓冲区。
 * 断言各级别 hook 调用次数、接收到的格式化负载包含对应级别 tag 与正文。
 *
 * 编译：OHOS clang（/data/service/hnp/bin/clang），链接安装的 libembedded-log.a
 * 运行：直接执行 ELF（OHOS PC 可执行），断言退出码 0。
 */
#include <stdio.h>
#include <string.h>
#include "log.h"

static char g_buff[1024];
static char g_last[1024];
static int g_rcv_count = 0;

static void sink(const char *s)
{
    g_rcv_count++;
    strncpy(g_last, s, sizeof(g_last) - 1);
    g_last[sizeof(g_last) - 1] = '\0';
}

static int check(const char *what, int cond)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    printf("PASS: %s\n", what);
    return 0;
}

int main(void)
{
    int fails = 0;
    unsigned char hexdata[] = {0xde, 0xad, 0xbe, 0xef, 0x01, 0x23};

    log_init(g_buff, sizeof(g_buff), sink);

    LOG_ERR("ohos-test-error %d", 1001);
    fails += check("LOG_ERR hook fired", g_rcv_count == 1);
    fails += check("LOG_ERR payload has tag", strstr(g_last, "[ERR] ") != NULL);
    fails += check("LOG_ERR payload has body", strstr(g_last, "ohos-test-error 1001") != NULL);

    LOG_WRN("ohos-test-warn %s", "w1");
    fails += check("LOG_WRN hook fired", g_rcv_count == 2);
    fails += check("LOG_WRN payload has body", strstr(g_last, "ohos-test-warn w1") != NULL);

    LOG_INF("ohos-test-info %x", 0x2a);
    fails += check("LOG_INF hook fired", g_rcv_count == 3);
    fails += check("LOG_INF payload has body", strstr(g_last, "ohos-test-info 2a") != NULL);

    printk_hex(hexdata, sizeof(hexdata));
    fails += check("printk_hex hook fired", g_rcv_count == 4);
    /* printk_hex 输出为空格分隔的十六进制字节 + ASCII 尾列 */
    fails += check("printk_hex dumps bytes", strstr(g_last, "de ad be ef 01 23") != NULL);

    if (fails == 0) {
        printf("OHOS test_ohos: ALL PASS (hook_calls=%d)\n", g_rcv_count);
        return 0;
    }
    fprintf(stderr, "OHOS test_ohos: %d assertion(s) failed\n", fails);
    return 1;
}
