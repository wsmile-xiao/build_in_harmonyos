/* test_easylogger — 消费者视角验证：通过公开 API 初始化、输出日志并校验结果 */
#define LOG_TAG "test"
#include <elog.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>

static pthread_mutex_t output_lock;
static char captured[8192];
static size_t captured_len = 0;

/* ── 简易 port 实现（测试用）：捕获输出到内存缓冲区 ── */
ElogErrCode elog_port_init(void) {
    pthread_mutex_init(&output_lock, NULL);
    return ELOG_NO_ERR;
}

void elog_port_output(const char *log, size_t size) {
    if (captured_len + size < sizeof(captured)) {
        memcpy(captured + captured_len, log, size);
        captured_len += size;
    }
    printf("%.*s", (int)size, log);
}

void elog_port_output_lock(void) {
    pthread_mutex_lock(&output_lock);
}

void elog_port_output_unlock(void) {
    pthread_mutex_unlock(&output_lock);
}

const char *elog_port_get_time(void) {
    static char t[24] = {0};
    time_t now = time(NULL);
    struct tm *p = localtime(&now);
    if (p) {
        snprintf(t, 18, "%02d-%02d %02d:%02d:%02d",
                 p->tm_mon + 1, p->tm_mday, p->tm_hour, p->tm_min, p->tm_sec);
    }
    return t;
}

const char *elog_port_get_p_info(void) {
    static char pi[10] = {0};
    snprintf(pi, 10, "pid:%04d", (int)getpid());
    return pi;
}

const char *elog_port_get_t_info(void) {
    static char ti[10] = {0};
    snprintf(ti, 10, "tid:%04lx", (unsigned long)pthread_self());
    return ti;
}

#define LOG_TAG "test"

int main(void) {
    int fail = 0;
    setbuf(stdout, NULL);
    printf("test_easylogger: init...\n");

    if (elog_init() != ELOG_NO_ERR) {
        printf("FAIL: elog_init() != ELOG_NO_ERR\n");
        return 1;
    }
    elog_set_fmt(ELOG_LVL_ASSERT, ELOG_FMT_ALL);
    elog_set_fmt(ELOG_LVL_INFO, ELOG_FMT_LVL | ELOG_FMT_TAG);
    elog_set_filter_lvl(ELOG_LVL_VERBOSE);
    elog_start();

    log_a("assert-marker");
    log_e("error-marker");
    log_w("warn-marker");
    log_i("info-marker");
    log_d("debug-marker");
    log_v("verbose-marker");
    elog_raw("raw-marker\n");

    /* 默认 elog_cfg.h 开启 ELOG_ASYNC_OUTPUT_ENABLE：日志先入异步缓冲，
       由独立线程消费输出。等待线程消费完成后再校验捕获缓冲区。 */
    usleep(1000 * 1000);

    printf("test_easylogger: captured=%zu bytes\n", captured_len);

    /* 校验捕获输出包含各级别标记 */
    const char *markers[] = {"assert-marker", "error-marker", "warn-marker",
                             "info-marker", "debug-marker", "verbose-marker", "raw-marker"};
    int i;
    for (i = 0; i < 7; i++) {
        if (strstr(captured, markers[i]) == NULL) {
            printf("FAIL: missing marker %s\n", markers[i]);
            fail = 1;
        }
    }

    if (strstr(captured, "EasyLogger V2.2.0") == NULL) {
        printf("FAIL: missing version banner\n");
        fail = 1;
    }

    if (fail) {
        printf("test_easylogger: FAILED\n");
        return 1;
    }
    printf("test_easylogger: PASSED\n");
    return 0;
}
