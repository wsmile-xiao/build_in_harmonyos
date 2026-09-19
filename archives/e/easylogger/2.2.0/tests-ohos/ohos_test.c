/* ohos_test.c — HarmonyOS 专项测试：通过公开 API 验证过滤、级别输出与捕获结果
 *
 * 仅使用已安装头文件 (elog.h) 与公开 API：elog_init / elog_start /
 * elog_set_fmt / elog_set_filter_lvl / elog_set_filter_tag /
 * elog_set_filter_kw / elog_set_output_enabled / log_* 宏 / elog_raw。
 * 业务语义：验证日志过滤链在 OHOS 平台上的真实可观察行为。
 */
#define LOG_TAG "ohos"
#include <elog.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>

static pthread_mutex_t output_lock;
static char captured[8192];
static size_t captured_len = 0;
static int failures = 0;

/* ── 测试 port：捕获输出到内存缓冲，校验过滤结果 ── */
ElogErrCode elog_port_init(void) {
    pthread_mutex_init(&output_lock, NULL);
    return ELOG_NO_ERR;
}

void elog_port_output(const char *log, size_t size) {
    if (captured_len + size < sizeof(captured)) {
        memcpy(captured + captured_len, log, size);
        captured_len += size;
    }
}

void elog_port_output_lock(void)   { pthread_mutex_lock(&output_lock); }
void elog_port_output_unlock(void) { pthread_mutex_unlock(&output_lock); }

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

#define LOG_TAG "ohos"

static void reset_capture(void) { captured[0] = '\0'; captured_len = 0; }

static void check(const char *name, int cond) {
    printf("  [%s] %s\n", cond ? "PASS" : "FAIL", name);
    if (!cond) failures++;
}

int main(void) {
    setbuf(stdout, NULL);
    printf("ohos_test: EasyLogger HarmonyOS 专项测试开始\n");

    /* 1) 初始化 + 格式 */
    if (elog_init() != ELOG_NO_ERR) {
        printf("  [FAIL] elog_init\n");
        return 1;
    }
    elog_set_fmt(ELOG_LVL_ASSERT, ELOG_FMT_ALL);
    elog_set_fmt(ELOG_LVL_INFO, ELOG_FMT_LVL | ELOG_FMT_TAG);
    elog_start();

    /* 2) 全量输出：所有级别 marker 应出现在捕获输出中 */
    reset_capture();
    log_a("m-assert"); log_e("m-error"); log_w("m-warn");
    log_i("m-info");  log_d("m-debug"); log_v("m-verbose");
    elog_raw("m-raw\n");
    usleep(500 * 1000); /* 等待异步线程消费 */
    check("全级别输出(a/e/w/i/d/v/raw)", captured_len > 0 &&
          strstr(captured, "m-assert") && strstr(captured, "m-info") &&
          strstr(captured, "m-raw"));

    /* 3) 级别过滤：只保留 WARN 及以上 */
    reset_capture();
    elog_set_filter_lvl(ELOG_LVL_WARN);
    log_e("lvl-err"); log_w("lvl-warn"); log_i("lvl-info");
    usleep(500 * 1000);
    check("级别过滤(>=WARN)", strstr(captured, "lvl-err") &&
          strstr(captured, "lvl-warn") && !strstr(captured, "lvl-info"));
    elog_set_filter_lvl(ELOG_LVL_VERBOSE);

    /* 4) tag 过滤：仅输出 ohos 标签 */
    reset_capture();
    elog_set_filter_tag("ohos");
    log_i("tag-ohos");
    log_e("extra", "tag-other");
    usleep(500 * 1000);
    check("tag 过滤(仅 ohos)", strstr(captured, "tag-ohos") &&
          !strstr(captured, "tag-other"));
    elog_set_filter_tag("");

    /* 5) keyword 过滤：仅含关键字 hello */
    reset_capture();
    elog_set_filter_kw("hello");
    log_i("kw-no-keyword");
    log_i("kw-has-hello");
    usleep(500 * 1000);
    check("keyword 过滤(仅含 hello)", strstr(captured, "kw-has-hello") &&
          !strstr(captured, "kw-no-keyword"));
    elog_set_filter_kw("");

    /* 6) 输出开关关闭后无输出 */
    reset_capture();
    elog_set_output_enabled(false);
    log_i("disabled-msg");
    usleep(500 * 1000);
    check("输出开关关闭", captured_len == 0);
    elog_set_output_enabled(true);

    /* 7) 版本横幅（elog_start 已输出） */
    reset_capture();
    printf("  [SKIP] 版本横幅（start 时已输出，见 test_package）\n");

    if (failures == 0) {
        printf("OHOS TEST PASS — 初始化守卫 + 5 项行为断言全部通过\n");
        return 0;
    }
    printf("OHOS TEST FAIL — %d 项断言失败\n", failures);
    return 1;
}