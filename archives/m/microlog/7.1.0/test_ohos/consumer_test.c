/*
 * consumer_test.c — microlog 7.1.0 消费者验证 + 鸿蒙专项测试程序
 *
 * 模拟业务上层组件: 仅通过已安装/导出的公开头文件 <ulog.h> 与公开 API
 * (ulog_topic_add / ulog_topic_info / ulog_level_to_string /
 * ulog_event_to_cstr / ulog_output_add_file / ulog_cleanup) 使用该三方库,
 * 覆盖主题路由、级别字符串、文件输出与事件格式化, 并断言可观察结果。
 * 文件输出写入可写目录 (不依赖 tmpfile, 规避平台临时目录限制)。
 */
#include <stdio.h>
#include <string.h>
#include <ulog.h>

static int g_handler_calls = 0;

static void capture_handler(ulog_event *ev, void *arg) {
    (void)arg;
    char buf[512];
    if (ev && ulog_event_to_cstr(ev, buf, sizeof(buf)) == ULOG_STATUS_OK) {
        if (strstr(buf, "topic-file-msg") != NULL) {
            g_handler_calls++;
        }
    }
}

int main(int argc, char **argv) {
    const char *outdir = (argc > 1) ? argv[1] : ".";
    char filepath[1024];
    snprintf(filepath, sizeof(filepath), "%s/ulog_file_out.txt", outdir);

    int failures = 0;

    /* 1. 自定义输出 handler 捕获事件 */
    ulog_output_id out = ulog_output_add(&capture_handler, NULL, ULOG_LEVEL_TRACE);
    if (out == ULOG_OUTPUT_INVALID) {
        fprintf(stderr, "FAIL: ulog_output_add()\n");
        failures++;
    }

    /* 2. 主题 API: 添加主题并按其路由日志 */
    ulog_topic_id tid = ulog_topic_add("consumer", ULOG_OUTPUT_ALL, ULOG_LEVEL_TRACE);
    if (tid == ULOG_TOPIC_ID_INVALID) {
        fprintf(stderr, "FAIL: ulog_topic_add()\n");
        failures++;
    }

    /* 3. 文件输出: 写入可写目录 (不依赖 tmpfile) */
    FILE *fp = fopen(filepath, "w");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: fopen(%s)\n", filepath);
        failures++;
    } else {
        ulog_output_id fid = ulog_output_add_file(fp, ULOG_LEVEL_TRACE);
        if (fid == ULOG_OUTPUT_INVALID) {
            fprintf(stderr, "FAIL: ulog_output_add_file()\n");
            failures++;
        }
        ulog_topic_info("consumer", "topic-file-msg hello from consumer");
        fflush(fp);
        fclose(fp);

        /* 校验文件内容 */
        char rbuf[512] = {0};
        FILE *rf = fopen(filepath, "r");
        if (rf) {
            size_t n = fread(rbuf, 1, sizeof(rbuf) - 1, rf);
            rbuf[n] = '\0';
            fclose(rf);
        }
        if (strstr(rbuf, "topic-file-msg") == NULL) {
            fprintf(stderr, "FAIL: file output missing message\n");
            failures++;
        }
    }

    /* 4. 级别字符串 (上游格式为定宽填充, 如 "INFO ") */
    const char *lv = ulog_level_to_string(ULOG_LEVEL_INFO);
    if (lv == NULL || strncmp(lv, "INFO", 4) != 0) {
        fprintf(stderr, "FAIL: ulog_level_to_string(INFO) = '%s'\n", lv ? lv : "(null)");
        failures++;
    }

    /* 5. handler 计数: 主题日志经 ULOG_OUTPUT_ALL 路由到自定义 handler */
    if (g_handler_calls == 0) {
        fprintf(stderr, "FAIL: capture handler did not observe topic message\n");
        failures++;
    }

    ulog_cleanup();

    if (failures == 0) {
        printf("PASS: consumer_test (topics/file-output/level/event OK, handler_calls=%d)\n",
               g_handler_calls);
        return 0;
    }
    printf("FAIL: %d check(s) failed\n", failures);
    return 1;
}