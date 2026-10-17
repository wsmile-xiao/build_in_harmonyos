/*
 * Consumer use case — lwprintf 1.1.0
 *
 * 模拟业务上层组件（嵌入式日志模块）：仅通过已安装包的公开头文件
 * "lwprintf/lwprintf.h" 与公开 API (lwprintf_snprintf_ex / lwprintf_init_ex)
 * 格式化日志行并收集到环形输出目标，验证可观察结果。
 *
 * 不包含库私有头文件、不调用内部符号、不复用库内部测试构建目录；
 * 通过公开链接目标 liblwprintf.a 与已安装 include/ 构建。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "lwprintf/lwprintf.h"

/* 日志采集缓冲：业务层输出目标 */
static char log_sink[512];
static size_t log_sink_len;

static int
log_output(int ch, lwprintf_t* lw) {
    (void)lw;
    if (ch != '\0' && log_sink_len < sizeof(log_sink) - 1) {
        log_sink[log_sink_len++] = (char)ch;
    }
    return ch;
}

int
main(void) {
    lwprintf_t log_instance;
    char line[128];
    int rc = 0;

    /* 初始化日志实例（公开 API #1: lwprintf_init_ex） */
    if (lwprintf_init_ex(&log_instance, log_output) != 1) {
        fprintf(stderr, "consumer: lwprintf_init_ex failed\n");
        return 1;
    }

    /* 业务: 格式化一条带级别的日志行（公开 API #2: lwprintf_snprintf_ex） */
    int n = lwprintf_snprintf_ex(&log_instance, line, sizeof(line),
                                 "[%s] %s: v=%d temp=%.1fC heap=%zuKB",
                                 "INFO", "sensor", 7, 36.6, (size_t)1024);
    if (n != 41) {
        fprintf(stderr, "consumer: unexpected length %d (expect 41)\n", n);
        rc = 1;
    }
    if (strcmp(line, "[INFO] sensor: v=7 temp=36.6C heap=1024KB") != 0) {
        fprintf(stderr, "consumer: unexpected content '%s'\n", line);
        rc = 1;
    }

    /* 把该日志行投递到业务日志目标，验证可观察输出 */
    log_sink_len = 0;
    lwprintf_printf_ex(&log_instance, "%s\n", line);
    if (log_sink_len != n + 1 || strncmp(log_sink, line, n) != 0) {
        fprintf(stderr, "consumer: log sink mismatch len=%u\n", (unsigned)log_sink_len);
        rc = 1;
    }

    /* 第二条日志：错误路径与十六进制转储（业务常用场景） */
    unsigned char frame[] = {0xDE, 0xAD, 0xBE, 0xEF};
    int n2 = lwprintf_snprintf_ex(&log_instance, line, sizeof(line),
                                  "[ERR] len=%d payload=%*K", 4, 4, frame);
    if (n2 != 28 || strcmp(line, "[ERR] len=4 payload=DEADBEEF") != 0) {
        fprintf(stderr, "consumer: hex dump mismatch len=%d line='%s'\n", n2, line);
        rc = 1;
    }

    if (rc == 0) {
        printf("consumer OK: log module formatted %d + %d chars via lwprintf public API\n",
               n, n2);
    }
    return rc;
}